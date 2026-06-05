"""Enllac determinista FEGA <-> Registre de SAT de la CV (Fase 3, segona font).

NO splink: enllac per NUCLI-SAT del nom (sense el prefix "SAT"/numero, que FEGA encasta de
forma inconsistent) + MUNICIPI, i a mes pel NUMERO DE REGISTRE extret del nom de FEGA contra
el Nº REGISTRO del directori. Emet sempre estat (match/possible/no-match) i traçabilitat, mai
un enllac dur. Sense CIF: s'arrossega el numero de registre com a identificador registral.
Mesura + mostra; NO toca el mart ni l'explorador. Reutilitza canon() de linkage/coverage.py.

Estats:
  - match    = numero de registre coincident (clau unica; nucli numeric, ignorant el sufix CV).
  - possible = nomes nucli-SAT del nom igual (aproximat), sense numero coincident.
  - no-match = res.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

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
    # El numero de registre es la clau UNICA -> senyal fort (match). El nucli-SAT del nom
    # (lossy) es nomes aproximat (possible). El municipi es conserva per a la mostra.
    con.execute(f"""
        create or replace temp view sat as
        select distinct nom as sat_nom, num_reg, municipi as sat_muni,
               {sat_core("nom")} as namekey
        from sat_raw where {sat_core("nom")} is not null
    """)
    con.execute(f"""
        create or replace temp view fega_ent as
        select clau, any_value(nom_canonic) as nom, sum(import_eur) as import_eur,
               max(municipi) as muni_fega, any_value({sat_core("nom_canonic")}) as namekey,
               any_value({regnum("nom_canonic")}) as regnum
        from fega where {sat_subset("nom_canonic")} group by clau
    """)
    # Candidats per NUMERO DE REGISTRE (clau unica) -> fort. El directori el porta amb sufix
    # d'ambit ("498CV") i FEGA encasta nomes el numero ("498"); es compara el NUCLI NUMERIC.
    # El nucli numeric pot conflar dos registres distints (nacional "15" vs autonomic "15CV"):
    # el NOM desambigua (si nomes una entrada casa tambe pel nucli-SAT del nom, eixa es la bona).
    con.execute("""
        create or replace temp view code_cand as
        select e.clau, s.num_reg, s.sat_nom, s.sat_muni,
               (s.namekey is not null and length(s.namekey) >= 4 and length(e.namekey) >= 4
                and (contains(e.namekey, s.namekey) or contains(s.namekey, e.namekey)))
                   as name_ok
        from fega_ent e
        join sat s
            on try_cast(regexp_replace(s.num_reg, '[^0-9]', '', 'g') as bigint)
               = try_cast(e.regnum as bigint)
        where e.regnum is not null
    """)
    con.execute("""
        create or replace temp view code_rank as
        select clau, num_reg, sat_nom, sat_muni, name_ok,
               count(*) over (partition by clau) as n_total,
               sum(case when name_ok then 1 else 0 end) over (partition by clau) as n_nameok
        from code_cand
    """)
    con.execute("""
        create or replace temp view reg_agg as
        select clau,
               case when n_total = 1 or n_nameok = 1 then 1 else n_total end as n_reg,
               arg_max(num_reg, case when name_ok then 2 when n_total = 1 then 1 else 0 end)
                   as num_reg,
               arg_max(sat_nom, case when name_ok then 2 when n_total = 1 then 1 else 0 end)
                   as sat_nom,
               arg_max(sat_muni, case when name_ok then 2 when n_total = 1 then 1 else 0 end)
                   as sat_muni
        from code_rank
        group by clau, n_total, n_nameok
    """)
    # Candidats per nucli-SAT del nom (>=4 caracters) -> aproximat.
    con.execute("""
        create or replace temp view name_agg as
        select e.clau, count(distinct s.sat_nom) as n_name,
               any_value(s.num_reg) as num_reg, any_value(s.sat_nom) as sat_nom,
               any_value(s.sat_muni) as sat_muni
        from fega_ent e join sat s on s.namekey = e.namekey and length(e.namekey) >= 4
        group by e.clau
    """)
    con.execute("""
        create or replace temp view classified as
        select
            e.clau, e.nom, e.import_eur, e.muni_fega,
            case when r.clau is not null and r.n_reg = 1 then 'confirmat'  -- codi unic
                 when r.clau is not null then 'ambigu'  -- codi amb >1 candidat
                 when n.clau is not null and n.n_name = 1 then 'confirmat'  -- nucli unic
                 when n.clau is not null then 'ambigu'  -- nucli amb >1 candidat
                 else 'no-match' end as tipus,
            case when r.clau is not null then 'codi'
                 when n.clau is not null then 'nucli' end as metode,
            coalesce(r.num_reg, n.num_reg) as num_registre,
            coalesce(r.sat_nom, n.sat_nom) as sat_nom,
            coalesce(r.sat_muni, n.sat_muni) as sat_muni,
            coalesce(r.n_reg, n.n_name, 0) as n_cand
        from fega_ent e
        left join reg_agg r on r.clau = e.clau
        left join name_agg n on n.clau = e.clau
    """)


def measure(con: duckdb.DuckDBPyConnection) -> dict:
    build_classified(con)
    row = con.execute("""
        select count(*) n, sum(import_eur) imp,
               count(*) filter (where tipus='confirmat') n_c,
               count(*) filter (where tipus='ambigu') n_a,
               count(*) filter (where tipus='no-match') n_nm,
               sum(import_eur) filter (where tipus='confirmat') imp_c,
               sum(import_eur) filter (where tipus='ambigu') imp_a
        from classified
    """).fetchone()
    n, imp, n_c, n_a, n_nm, imp_c, imp_a = (x or 0 for x in row)
    amb = con.execute("""
        select count(*) filter (where tipus in ('confirmat','ambigu')) tot,
               count(*) filter (where tipus='ambigu') ambig
        from classified
    """).fetchone()
    amb_ex = con.execute("""
        select nom, sat_nom, n_cand, round(import_eur) imp from classified
        where tipus='ambigu' order by import_eur desc limit 8
    """).fetchall()
    return {
        "n": n,
        "imp": imp,
        "n_confirmat": n_c,
        "n_ambigu": n_a,
        "n_nomatch": n_nm,
        "imp_confirmat": imp_c,
        "imp_ambigu": imp_a,
        "ambig_total": amb[0] or 0,
        "ambig_n": amb[1] or 0,
        "ambig_examples": amb_ex,
    }


def write_sample(con: duckdb.DuckDBPyConnection, path: Path = SAMPLE_CSV, n: int = 40) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        copy (
            select nom as fega_nom, sat_nom, tipus, metode,
                   muni_fega as municipi_fega, sat_muni as municipi_sat,
                   n_cand as candidats_sat, num_registre as numero_registre,
                   round(import_eur) as import_eur, '' as veredicte_humà
            from classified where tipus in ('confirmat','ambigu')
            order by tipus, import_eur desc limit {n}
        ) to '{path.as_posix()}' (header, delimiter ',')
    """)
    return path


def _fmt(r: dict) -> str:
    nn = r["n"] or 1
    cov_n = 100 * (r["n_confirmat"] + r["n_ambigu"]) / nn
    cov_e = 100 * (r["imp_confirmat"] + r["imp_ambigu"]) / r["imp"] if r["imp"] else 0
    amb_pct = 100 * r["ambig_n"] / r["ambig_total"] if r["ambig_total"] else 0
    pc, pa, pnm = 100 * r["n_confirmat"] / nn, 100 * r["n_ambigu"] / nn, 100 * r["n_nomatch"] / nn
    lines = [
        "=== ENLLAC FEGA x SAT de la CV (numero de registre + nucli-SAT del nom) ===",
        f"\nSUBCONJUNT SAT de FEGA: {r['n']:,} entitats, {r['imp']:,.0f} EUR",
        f"  confirmat {r['n_confirmat']:>4,}  ({pc:.1f}%)  {r['imp_confirmat']:>13,.0f} EUR",
        f"  ambigu    {r['n_ambigu']:>4,}  ({pa:.1f}%)  {r['imp_ambigu']:>13,.0f} EUR",
        f"  no-match  {r['n_nomatch']:>4,}  ({pnm:.1f}%)",
        f"  => cobertura (confirmat+ambigu): {cov_n:.1f}% entitats, {cov_e:.1f}% euros",
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
