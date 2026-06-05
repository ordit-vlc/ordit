"""Enllac determinista FEGA <-> Registre de SAT de la CV (Fase 3, segona font).

NO splink: enllac per NUCLI-SAT del nom (sense el prefix "SAT"/numero, que FEGA encasta de
forma inconsistent) + MUNICIPI, i a mes pel NUMERO DE REGISTRE extret del nom de FEGA contra
el Nº REGISTRO del directori. Emet sempre estat (match/possible/no-match) i traçabilitat, mai
un enllac dur. Sense CIF: s'arrossega el numero de registre com a identificador registral.
Mesura + mostra; NO toca el mart ni l'explorador. Reutilitza canon() de linkage/coverage.py.

Principi: el numero que FEGA encasta al nom pot estar MAL ESCRIT -> nom + municipi son
l'autoritat, el numero nomes corrobora. Es puntua cada candidat (nom 4 + numero 2 + municipi 1).
  - confirmat = una sola entrada amb la millor puntuacio.
  - ambigu    = empat al cim (>=2 entrades igual de plausibles).
  - no-match  = res.
metode: codi / rescat (numero erroni rescatat pel nom) / nom+municipi / nucli.
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


def sat_namekey(col: str) -> str:
    """Clau de nom robusta per a SAT: lleva els tokens de forma/registre (SAT/NUM/N/CV...) i
    qualsevol token que comence per digit (numeros purs i numero+ambit "265CV"), parteix en
    paraules, les ORDENA i les concatena. Aixi neutralitza la inversio d'article i l'ordre de
    paraules ("LA SOLANA" = "SOLANA, LA"). Replica sat_namekey() de la macro dbt.
    """
    s = f"' ' || upper(strip_accents({col})) || ' '"
    s = f"regexp_replace({s}, '[^A-Z0-9]', ' ', 'g')"
    s = f"regexp_replace({s}, ' ({SAT_TOKENS}) ', ' ', 'g')"
    s = f"regexp_replace({s}, ' ({SAT_TOKENS}) ', ' ', 'g')"
    s = f"regexp_replace({s}, ' [0-9][A-Z0-9]* ', ' ', 'g')"
    return (
        "nullif(array_to_string(list_sort(list_filter("
        f"string_split_regex(trim({s}), '[^A-Z0-9]+'), x -> length(x) >= 1)), ''), '')"
    )


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


def _muni_norm(col: str) -> str:
    return f"nullif(regexp_replace(upper(strip_accents({col})), '[^A-Z0-9]', '', 'g'), '')"


def build_classified(con: duckdb.DuckDBPyConnection) -> None:
    """Construeix `classified` (un registre per entitat SAT de FEGA). Requereix `fega` i
    `sat_raw`.

    El numero que FEGA encasta al nom pot estar MAL ESCRIT, aixi que NO es clau infal·lible. El
    senyal mes robust es NOM + MUNICIPI; el numero nomes corrobora. Es puntua cada entrada del
    directori candidata (nom 4 + numero 2 + municipi 1) i guanya la de millor puntuacio:
    confirmat si nomes una hi empata al cim, ambigu si >=2, no-match si cap.
    """
    con.execute(f"""
        create or replace temp view dir as
        select distinct nom as sat_nom, num_reg, municipi as sat_muni,
               try_cast(regexp_replace(num_reg, '[^0-9]', '', 'g') as bigint) as num_core,
               {sat_namekey("nom")} as namekey, {_muni_norm("municipi")} as muni
        from sat_raw
    """)
    con.execute(f"""
        create or replace temp view fega_ent as
        select clau, any_value(nom_canonic) as nom, sum(import_eur) as import_eur,
               max(municipi) as muni_fega, any_value({sat_namekey("nom_canonic")}) as namekey,
               any_value({regnum("nom_canonic")}) as regnum, max({_muni_norm("municipi")}) as muni
        from fega where {sat_subset("nom_canonic")} group by clau
    """)
    # Candidata si casa pel NOM (tokens ordenats) o pel NUMERO. Tres senyals per separat.
    con.execute("""
        create or replace temp view cand as
        select f.clau, f.regnum as fega_regnum, d.num_reg, d.sat_nom, d.sat_muni,
               (f.namekey is not null and length(f.namekey) >= 4 and d.namekey = f.namekey)
                   as name_ok,
               (f.regnum is not null and d.num_core = try_cast(f.regnum as bigint)) as num_ok,
               (f.muni is not null and d.muni is not null and length(f.muni) >= 4
                and (contains(d.muni, f.muni) or contains(f.muni, d.muni))) as muni_ok
        from fega_ent f join dir d
          on (f.namekey is not null and length(f.namekey) >= 4 and d.namekey = f.namekey)
          or (f.regnum is not null and d.num_core = try_cast(f.regnum as bigint))
    """)
    # Puntuacio: nom 4 (autoritat) + numero 2 (corroboracio) + municipi 1 (desempat).
    con.execute("""
        create or replace temp view scored as
        select *, (case when name_ok then 4 else 0 end)
                   + (case when num_ok then 2 else 0 end)
                   + (case when muni_ok then 1 else 0 end) as score
        from cand
    """)
    con.execute("""
        create or replace temp view ranked as
        select *, max(score) over (partition by clau) as best,
               row_number() over (partition by clau order by score desc, num_ok desc, num_reg)
                   as rn
        from scored
    """)
    con.execute("""
        create or replace temp view ranked2 as
        select *, count(*) filter (where score = best) over (partition by clau) as n_top
        from ranked
    """)
    con.execute("create or replace temp view winner as select * from ranked2 where rn = 1")
    con.execute("""
        create or replace temp view classified as
        select
            e.clau, e.nom, e.import_eur, e.muni_fega,
            case when w.clau is null then 'no-match'
                 when w.n_top = 1 then 'confirmat' else 'ambigu' end as tipus,
            case when w.clau is null then null
                 when w.num_ok then 'codi'  -- el numero corrobora
                 when w.fega_regnum is not null then 'rescat'  -- numero erroni; nom el rescata
                 when w.muni_ok then 'nom+municipi'  -- sense numero; nom + municipi
                 else 'nucli' end as metode,  -- sense numero ni municipi; nomes nom
            w.num_reg as num_registre, w.sat_nom, w.sat_muni,
            coalesce(w.n_top, 0) as n_cand
        from fega_ent e
        left join winner w on w.clau = e.clau
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
