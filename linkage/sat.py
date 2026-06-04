"""Enllac determinista FEGA <-> Registre de SAT de la CV (Fase 3, segona font).

NO splink: enllac per NUCLI-SAT del nom (sense el prefix "SAT"/numero, que FEGA encasta de
forma inconsistent) + MUNICIPI, i a mes pel NUMERO DE REGISTRE extret del nom de FEGA contra
el Nº REGISTRO del directori. Emet sempre estat (match/possible/no-match) i traçabilitat, mai
un enllac dur. Sense CIF: s'arrossega el numero de registre com a identificador registral.
Mesura + mostra; NO toca el mart ni l'explorador. Reutilitza canon() de linkage/coverage.py.

Estats:
  - match    = nucli-SAT del nom igual I municipi coincident.
  - possible = nucli-SAT igual amb municipi distint/sense resoldre, O numero de registre igual.
  - no-match = res.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from linkage.coverage import canon

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("linkage.sat")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ordit.duckdb"
SAT_DIR = ROOT / "data" / "raw" / "sat"
SAMPLE_CSV = ROOT / "data" / "linkage_sample_fega_sat.csv"

# Subconjunt SAT de FEGA (heuristica per forma).
SAT_TOKENS = "SAT|NUM|N|CV|SDAD|SOCIEDAD|AGRARIA|TRANSFORMACION|LTDA|LIMITADA"


def sat_subset(col: str) -> str:
    return (
        f"regexp_matches(upper(strip_accents({col})), '(^|[^A-Z])(SAT)([^A-Z]|$)|SOCIEDAD AGRARIA')"
    )


def sat_core(col: str) -> str:
    """Nucli-SAT: nom sense els tokens de forma/registre (SAT/NUM/N/CV...) ni numeros.

    FEGA encasta "SAT <num>" al nom de forma inconsistent; el directori porta la denominacio
    neta. El nucli alinea els dos costats. Dues passades per als tokens consecutius.
    """
    s = f"' ' || upper(strip_accents({col})) || ' '"
    s = f"regexp_replace({s}, '[^A-Z0-9]', ' ', 'g')"
    s = f"regexp_replace({s}, ' ({SAT_TOKENS}) ', ' ', 'g')"
    s = f"regexp_replace({s}, ' ({SAT_TOKENS}) ', ' ', 'g')"
    s = f"regexp_replace({s}, ' [0-9]+ ', ' ', 'g')"
    return f"nullif(regexp_replace({s}, '[^A-Z0-9]', '', 'g'), '')"


def regnum(col: str) -> str:
    """Numero de registre: la primera seqüencia de >=2 xifres del nom de FEGA."""
    return f"nullif(regexp_extract(upper(strip_accents({col})), '([0-9][0-9]+)', 1), '')"


def load_sat(con: duckdb.DuckDBPyConnection, sat_dir: Path = SAT_DIR) -> int:
    files = sorted(sat_dir.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(
            f"sense JSONL de SAT a {sat_dir}; executa `python -m ingest.sat.download`"
        )
    glob = str(sat_dir / "*.jsonl")
    con.execute(
        "create or replace temp view sat_raw as "
        'select "DENOMINACIÓN" as nom, "Nº REGISTRO" as num_reg, "MUNICIPIO" as municipi '
        f"from read_json_auto('{glob}')"
    )
    return con.execute("select count(*) from sat_raw").fetchone()[0]


def build_classified(con: duckdb.DuckDBPyConnection) -> None:
    """Construeix `classified` (un registre per entitat SAT de FEGA). Requereix `fega` i
    `sat_raw`."""
    con.execute(f"""
        create or replace temp view sat as
        select distinct nom as sat_nom, num_reg, municipi as sat_muni,
               {sat_core("nom")} as namekey, {canon("municipi")} as muni_ck
        from sat_raw where {sat_core("nom")} is not null
    """)
    con.execute(f"""
        create or replace temp view fega_ent as
        select clau, any_value(nom_canonic) as nom, sum(import_eur) as import_eur,
               max(municipi) as muni_fega, any_value({sat_core("nom_canonic")}) as namekey,
               any_value({regnum("nom_canonic")}) as regnum
        from fega where {sat_subset("nom_canonic")} group by clau
    """)
    con.execute(f"""
        create or replace temp view fega_muni as
        select distinct clau, {canon("municipi")} as muni_ck
        from fega where {sat_subset("nom_canonic")} and municipi is not null
    """)
    # Candidats per nucli-SAT del nom (>=4 caracters), amb si el municipi coincideix.
    con.execute("""
        create or replace temp view name_cand as
        select e.clau, s.sat_nom, s.num_reg, s.sat_muni,
               exists (select 1 from fega_muni m where m.clau = e.clau and m.muni_ck = s.muni_ck)
                   as muni_ok
        from fega_ent e join sat s on s.namekey = e.namekey and length(e.namekey) >= 4
    """)
    con.execute("""
        create or replace temp view name_agg as
        select clau, count(distinct sat_nom) as n_name, bool_or(muni_ok) as has_muni,
               arg_max(num_reg, muni_ok::int) as num_reg,
               arg_max(sat_nom, muni_ok::int) as sat_nom,
               arg_max(sat_muni, muni_ok::int) as sat_muni
        from name_cand group by clau
    """)
    # Candidats per numero de registre (nomes per a entitats sense candidat de nom).
    con.execute("""
        create or replace temp view reg_agg as
        select e.clau, count(distinct s.sat_nom) as n_reg,
               any_value(s.num_reg) as num_reg, any_value(s.sat_nom) as sat_nom,
               any_value(s.sat_muni) as sat_muni
        from fega_ent e
        join sat s on try_cast(s.num_reg as bigint) = try_cast(e.regnum as bigint)
        where e.regnum is not null and e.clau not in (select clau from name_agg)
        group by e.clau
    """)
    con.execute("""
        create or replace temp view classified as
        select
            e.clau, e.nom, e.import_eur, e.muni_fega,
            case when n.has_muni then 'match'
                 when n.clau is not null then 'possible'
                 when r.clau is not null then 'possible'
                 else 'no-match' end as tipus,
            coalesce(n.num_reg, r.num_reg) as num_registre,
            coalesce(n.sat_nom, r.sat_nom) as sat_nom,
            coalesce(n.sat_muni, r.sat_muni) as sat_muni,
            coalesce(n.n_name, r.n_reg, 0) as n_cand
        from fega_ent e
        left join name_agg n on n.clau = e.clau
        left join reg_agg r on r.clau = e.clau
    """)


def measure(con: duckdb.DuckDBPyConnection) -> dict:
    build_classified(con)
    row = con.execute("""
        select count(*) n, sum(import_eur) imp,
               count(*) filter (where tipus='match') n_m,
               count(*) filter (where tipus='possible') n_p,
               count(*) filter (where tipus='no-match') n_nm,
               sum(import_eur) filter (where tipus='match') imp_m,
               sum(import_eur) filter (where tipus='possible') imp_p
        from classified
    """).fetchone()
    n, imp, n_m, n_p, n_nm, imp_m, imp_p = (x or 0 for x in row)
    amb = con.execute("""
        select count(*) filter (where tipus in ('match','possible')) tot,
               count(*) filter (where tipus in ('match','possible') and n_cand > 1) ambig
        from classified
    """).fetchone()
    amb_ex = con.execute("""
        select nom, sat_nom, n_cand, round(import_eur) imp from classified
        where tipus in ('match','possible') and n_cand > 1 order by import_eur desc limit 8
    """).fetchall()
    return {
        "n": n,
        "imp": imp,
        "n_match": n_m,
        "n_possible": n_p,
        "n_nomatch": n_nm,
        "imp_match": imp_m,
        "imp_possible": imp_p,
        "ambig_total": amb[0] or 0,
        "ambig_n": amb[1] or 0,
        "ambig_examples": amb_ex,
    }


def write_sample(con: duckdb.DuckDBPyConnection, path: Path = SAMPLE_CSV, n: int = 40) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        copy (
            select nom as fega_nom, sat_nom, tipus,
                   muni_fega as municipi_fega, sat_muni as municipi_sat,
                   n_cand as candidats_sat, num_registre as numero_registre,
                   round(import_eur) as import_eur, '' as veredicte_humà
            from classified where tipus in ('match','possible')
            order by tipus, import_eur desc limit {n}
        ) to '{path.as_posix()}' (header, delimiter ',')
    """)
    return path


def _fmt(r: dict) -> str:
    nn = r["n"] or 1
    cov_n = 100 * (r["n_match"] + r["n_possible"]) / nn
    cov_e = 100 * (r["imp_match"] + r["imp_possible"]) / r["imp"] if r["imp"] else 0
    amb_pct = 100 * r["ambig_n"] / r["ambig_total"] if r["ambig_total"] else 0
    pm, pp, pnm = 100 * r["n_match"] / nn, 100 * r["n_possible"] / nn, 100 * r["n_nomatch"] / nn
    lines = [
        "=== ENLLAC FEGA x SAT de la CV (nucli-SAT + numero de registre + municipi) ===",
        f"\nSUBCONJUNT SAT de FEGA: {r['n']:,} entitats, {r['imp']:,.0f} EUR",
        f"  match    {r['n_match']:>4,}  ({pm:.1f}%)  {r['imp_match']:>13,.0f} EUR",
        f"  possible {r['n_possible']:>4,}  ({pp:.1f}%)  {r['imp_possible']:>13,.0f} EUR",
        f"  no-match {r['n_nomatch']:>4,}  ({pnm:.1f}%)",
        f"  => cobertura (match+possible): {cov_n:.1f}% entitats, {cov_e:.1f}% euros",
        f"\nAMBIGUITAT (nom >1 SAT): {r['ambig_n']:,}/{r['ambig_total']:,} ({amb_pct:.1f}%)",
    ]
    for nom, sat_nom, n_cand, imp in r["ambig_examples"]:
        lines.append(f"    {imp:>11,.0f} EUR  [{n_cand} cand.]  {nom[:38]}  ~  {sat_nom[:30]}")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover
    if not DB_PATH.exists():
        raise FileNotFoundError(f"sense {DB_PATH}; executa `just build` abans de l'enllac.")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        n_sat = load_sat(con)
        logger.info("SAT CV carregades: %d registres", n_sat)
        con.execute(
            "create or replace temp view fega as "
            "select clau_beneficiari as clau, nom_canonic, municipi, import_eur "
            "from mart_ajudes_pac"
        )
        report = measure(con)
        print(_fmt(report))
        path = write_sample(con)
        print(f"\nMostra per etiquetar (match+possible, amb municipi i numero de registre): {path}")
    finally:
        con.close()


if __name__ == "__main__":  # pragma: no cover
    main()
