"""Enllac determinista FEGA <-> Directori de Cooperatives de la CV (Fase 3, primera font).

NO splink: enllac per CLAU CANONICA (la mateixa de canon_beneficiari) + MUNICIPI com a
desambiguador. Emet sempre estat (match / possible / no-match) i traçabilitat, mai un enllac
dur. En match/possible arrossega el CIF i la clau registral de la cooperativa (el premi:
injecta a FEGA el CIF que no te). Reutilitza les utilitats de l'spike (linkage/coverage.py).

Estats (denominacions uniques al registre -> el municipi no discrimina):
  - match    = clau canonica EXACTA i candidat UNIC (per CIF), siga quin siga el municipi.
  - possible = nomes els incerts: nucli igual (aproximat) o clau exacta amb >1 CIF distint.
  - no-match = res.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from linkage.coverage import canon, core

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("linkage.cooperatives")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ordit.duckdb"
COOP_DIR = ROOT / "data" / "raw" / "cooperatives"
SAMPLE_CSV = ROOT / "data" / "linkage_sample_fega_cooperatives.csv"


# Subconjunt cooperatiu de FEGA (heuristica per forma): COOP / SCV / SCA / SCCL / COOPERATIVA.
def cooperativa(col: str) -> str:
    return (
        f"regexp_matches(upper(strip_accents({col})), "
        "'(^|[^A-Z])(COOP|SDAD COOP|SCV|SCA|SCCL)([^A-Z]|$)|COOPERATIVA|SOCIEDAD COOPERATIVA')"
    )


def load_cooperatives(con: duckdb.DuckDBPyConnection, coop_dir: Path = COOP_DIR) -> int:
    files = sorted(coop_dir.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(
            f"sense JSONL de cooperatives a {coop_dir}; executa "
            "`python -m ingest.cooperatives.download`"
        )
    glob = str(coop_dir / "*.jsonl")
    con.execute(
        "create or replace temp view coop_raw as "
        'select "DS_RAZON_SOCIAL" as nom, "CD_NIF" as cif, '
        '"CD_CLAVE_REGISTRAL" as clau_reg, "DS_MUNICIPIO" as municipi '
        f"from read_json_auto('{glob}')"
    )
    return con.execute("select count(*) from coop_raw").fetchone()[0]


def build_classified(con: duckdb.DuckDBPyConnection) -> None:
    """Construeix la taula `classified` (un registre per entitat cooperativa de FEGA).

    Requereix les vistes `fega` (nom, nom_canonic, import_eur, clau, municipi) i `coop_raw`.
    """
    # El registre certifica denominacions UNIQUES: nom canonic exacte + candidat unic = match,
    # siga quin siga el municipi (la diferencia de municipi es quasi sempre grafia bilingue del
    # mateix poble). El municipi es conserva nomes per a la mostra, no discrimina l'estat.
    con.execute(f"""
        create or replace temp view coop as
        select distinct nom as coop_nom, cif, clau_reg, municipi as coop_muni,
               {canon("nom")} as ck, {core("nom")} as core
        from coop_raw where {canon("nom")} is not null
    """)
    con.execute(f"""
        create or replace temp view fega_ent as
        select clau, any_value(nom_canonic) as nom, sum(import_eur) as import_eur,
               max(municipi) as muni_fega, any_value({core("nom_canonic")}) as core
        from fega where {cooperativa("nom_canonic")} group by clau
    """)
    # Candidats per clau canonica EXACTA: n_ck = nombre de cooperatives DISTINTES per CIF (la
    # clau legal), no per cadena de nom -> una mateixa coop duplicada al directori (mateix CIF,
    # puntuacio distinta) val 1, no 2. El normal es 1 (denominacions uniques).
    con.execute("""
        create or replace temp view ck_agg as
        select e.clau, count(distinct c.cif) as n_ck,
               any_value(c.cif) as cif, any_value(c.clau_reg) as clau_reg,
               any_value(c.coop_nom) as coop_nom, any_value(c.coop_muni) as coop_muni
        from fega_ent e join coop c on c.ck = e.clau
        group by e.clau
    """)
    # Candidats per nucli (aproximat), nomes per a entitats sense candidat de clau exacta.
    con.execute("""
        create or replace temp view core_agg as
        select e.clau, count(distinct c.cif) as n_core,
               any_value(c.cif) as cif, any_value(c.clau_reg) as clau_reg,
               any_value(c.coop_nom) as coop_nom, any_value(c.coop_muni) as coop_muni
        from fega_ent e join coop c on c.core = e.core and length(e.core) >= 5
        where e.clau not in (select clau from ck_agg)
        group by e.clau
    """)
    con.execute("""
        create or replace temp view classified as
        select
            e.clau, e.nom, e.import_eur, e.muni_fega,
            case when k.clau is not null and k.n_ck = 1 then 'confirmat'  -- exacte unic
                 when k.clau is not null then 'ambigu'  -- exacte amb >1 candidat
                 when c.clau is not null and c.n_core = 1 then 'confirmat'  -- nucli unic
                 when c.clau is not null then 'ambigu'  -- nucli amb >1 candidat
                 else 'no-match' end as tipus,
            case when k.clau is not null then 'exacte'
                 when c.clau is not null then 'nucli' end as metode,
            coalesce(k.cif, c.cif) as cif,
            coalesce(k.clau_reg, c.clau_reg) as clau_reg,
            coalesce(k.coop_nom, c.coop_nom) as coop_nom,
            coalesce(k.coop_muni, c.coop_muni) as coop_muni,
            coalesce(k.n_ck, c.n_core, 0) as n_cand
        from fega_ent e
        left join ck_agg k on k.clau = e.clau
        left join core_agg c on c.clau = e.clau
    """)


def measure(con: duckdb.DuckDBPyConnection) -> dict:
    build_classified(con)
    row = con.execute("""
        select count(*) n, sum(import_eur) imp,
               count(*) filter (where tipus='confirmat') n_c,
               count(*) filter (where tipus='ambigu') n_a,
               count(*) filter (where tipus='no-match') n_nm,
               sum(import_eur) filter (where tipus='confirmat') imp_c,
               sum(import_eur) filter (where tipus='ambigu') imp_a,
               count(*) filter (where tipus in ('confirmat','ambigu') and cif is not null) n_cif
        from classified
    """).fetchone()
    n, imp, n_c, n_a, n_nm, imp_c, imp_a, n_cif = (x or 0 for x in row)
    amb = con.execute("""
        select count(*) filter (where tipus in ('confirmat','ambigu')) tot,
               count(*) filter (where tipus='ambigu') ambig
        from classified
    """).fetchone()
    amb_ex = con.execute("""
        select nom, coop_nom, n_cand, round(import_eur) imp from classified
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
        "n_cif": n_cif,
        "ambig_total": amb[0] or 0,
        "ambig_n": amb[1] or 0,
        "ambig_examples": amb_ex,
    }


def write_sample(con: duckdb.DuckDBPyConnection, path: Path = SAMPLE_CSV, n: int = 40) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        copy (
            select nom as fega_nom, coop_nom, tipus, metode,
                   muni_fega as municipi_fega, coop_muni as municipi_coop,
                   n_cand as candidats_coop, cif as cif_candidat, clau_reg as clau_registral,
                   round(import_eur) as import_eur, '' as veredicte_humà
            from classified where tipus in ('confirmat','ambigu')
            order by tipus, import_eur desc limit {n}
        ) to '{path.as_posix()}' (header, delimiter ',')
    """)
    return path


def _fmt(r: dict) -> str:
    n = r["n"] or 1
    cov_n = 100 * (r["n_confirmat"] + r["n_ambigu"]) / n
    cov_e = 100 * (r["imp_confirmat"] + r["imp_ambigu"]) / r["imp"] if r["imp"] else 0
    amb_pct = 100 * r["ambig_n"] / r["ambig_total"] if r["ambig_total"] else 0
    pc, pa, pnm = 100 * r["n_confirmat"] / n, 100 * r["n_ambigu"] / n, 100 * r["n_nomatch"] / n
    lines = [
        "=== ENLLAC FEGA x Cooperatives CV (determinista, per nom canonic) ===",
        f"\nSUBCONJUNT COOPERATIU de FEGA: {r['n']:,} entitats, {r['imp']:,.0f} EUR",
        f"  confirmat {r['n_confirmat']:>5,}  ({pc:.1f}%)  {r['imp_confirmat']:>13,.0f} EUR",
        f"  ambigu    {r['n_ambigu']:>5,}  ({pa:.1f}%)  {r['imp_ambigu']:>13,.0f} EUR",
        f"  no-match  {r['n_nomatch']:>5,}  ({pnm:.1f}%)",
        f"  => cobertura (confirmat+ambigu): {cov_n:.1f}% entitats, {cov_e:.1f}% euros",
        f"\nCIF GUANYATS (entitats enllacades amb CIF de cooperativa): {r['n_cif']:,}",
        f"AMBIGUITAT (clau >1 cooperativa): {r['ambig_n']:,}/{r['ambig_total']:,} ({amb_pct:.1f}%)",
    ]
    for nom, coop_nom, n_cand, imp in r["ambig_examples"]:
        lines.append(f"    {imp:>12,.0f} EUR  [{n_cand} cand.]  {nom[:38]}  ~  {coop_nom[:32]}")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover
    if not DB_PATH.exists():
        raise FileNotFoundError(f"sense {DB_PATH}; executa `just build` abans de l'enllac.")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        n_coop = load_cooperatives(con)
        logger.info("Cooperatives CV carregades: %d registres", n_coop)
        con.execute("""
            create or replace temp view fega as
            select clau_beneficiari as clau, nom_canonic, municipi,
                   import_eur
            from mart_ajudes_pac
        """)
        report = measure(con)
        print(_fmt(report))
        path = write_sample(con)
        print(f"\nMostra per etiquetar (match+possible, amb municipi i CIF candidat): {path}")
    finally:
        con.close()


if __name__ == "__main__":  # pragma: no cover
    main()
