"""Spike de viabilitat de l'enllac FEGA x BORME per nom (Fase 3, pas 1).

Mesura, NO produccio: classifica cada beneficiari JURIDIC de FEGA en match / possible /
no-match contra la llosa de BORME, i reporta cobertura (entitats i euros), ambiguitat i una
mostra per etiquetar a ma. Cap enllac dur, cap dada publicada. Vegeu docs/sources/borme.md i
el PR de l'spike.

La clau canonica es EXACTAMENT la del macro dbt canon_beneficiari (plega accents + majuscules
+ elimina tot allo no alfanumeric), aplicada igual a FEGA i a BORME via DuckDB.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("linkage.coverage")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ordit.duckdb"
BORME_DIR = ROOT / "data" / "raw" / "borme"
SAMPLE_CSV = ROOT / "data" / "linkage_sample_fega_borme.csv"


# --- Normalitzacio (identica al macro canon_beneficiari) i nucli sense forma juridica -----
def canon(col: str) -> str:
    return f"nullif(regexp_replace(upper(strip_accents({col})), '[^A-Z0-9]', '', 'g'), '')"


# Nucli = nom canonic SENSE les paraules de forma juridica (per a pontejar "SL" vs "SOCIEDAD
# LIMITADA"). Treballa sobre la versio amb espais i despres lleva-ho tot menys alfanumeric.
_LEGAL = (
    "SL|SA|SLU|SAU|SLL|SLP|SAL|SCV|SCA|SCCL|SC|SCP|CB|SAT|COOP|COOPERATIVA|SDAD|"
    "SOCIEDAD|LIMITADA|ANONIMA|ANONIMA LABORAL|CIVIL|AGRARIA|TRANSFORMACION|VALENCIANA|CV"
)


def core(col: str) -> str:
    spaced = f"regexp_replace(' ' || upper(strip_accents({col})) || ' ', '[^A-Z0-9]', ' ', 'g')"
    no_legal = f"regexp_replace({spaced}, '( )({_LEGAL})( )', ' ', 'g')"
    # dos passades per als tokens de forma consecutius (p. ex. "SOCIEDAD LIMITADA")
    no_legal2 = f"regexp_replace({no_legal}, '( )({_LEGAL})( )', ' ', 'g')"
    return f"nullif(regexp_replace({no_legal2}, '[^A-Z0-9]', '', 'g'), '')"


# Heuristica: beneficiari amb pinta d'empresa/organisme (sense columna juridica a FEGA).
JURIDIC = (
    "regexp_matches(upper(strip_accents(nom)), '(^|[^A-Z])"
    "(SL|SA|SAT|SAU|SLU|SLL|SCCL|SCV|SCA|CB|SC|SCP|SLP|SAL|AIE|UTE|COOP|SDAD COOP)([^A-Z]|$)"
    "|FUNDACION|FUNDACIO|ASOCIACION|ASSOCIACIO|COOPERATIVA"
    "|SOCIEDAD (LIMITADA|ANONIMA|COOPERATIVA|CIVIL|AGRARIA)"
    "|COMUNIDAD DE (REGANTES|BIENES)|COMUNITAT DE (REGANTS|BENS)"
    "|AYUNTAMIENTO|AJUNTAMENT|GENERALITAT|DIPUTACI|MANCOMUNI|CONSORCI|CONSELL"
    "|UNIVERSITAT|UNIVERSIDAD|REGANTES|REGANTS')"
)
# Mercantil = societat de capital (elegible BORME): SL/SA i variants, i NO coop/SAT/CB/SC/public.
MERCANTIL = (
    "(regexp_matches(upper(strip_accents(nom)), "
    "'(^|[^A-Z])(SL|SA|SLU|SAU|SLL|SLP|SAL)([^A-Z]|$)|SOCIEDAD LIMITADA|SOCIEDAD ANONIMA') "
    "and not regexp_matches(upper(strip_accents(nom)), "
    "'(^|[^A-Z])(COOP|SDAD COOP|SCV|SCA|SCCL|SAT|CB|SC|SCP)([^A-Z]|$)"
    "|COOPERATIVA|SOCIEDAD (COOPERATIVA|CIVIL|AGRARIA)|COMUNIDAD DE (REGANTES|BIENES)"
    "|COMUNITAT DE (REGANTS|BENS)|REGANTES|REGANTS|AYUNTAMIENTO|AJUNTAMENT|GENERALITAT'))"
)


def build_views(con: duckdb.DuckDBPyConnection) -> None:
    """A partir de `fega(nom, import_eur)` i `borme(nom)`, crea les vistes de l'analisi.

    `fega` ha de tindre una fila per ENTITAT juridica (nom representatiu + import sumat).
    `borme` una fila per registre (es dedupe aci).
    """
    con.execute(f"""
        create or replace temp view fega_j as
        select nom, import_eur, {canon("nom")} as ck, {core("nom")} as core,
               {MERCANTIL} as mercantil
        from fega where {JURIDIC} and {canon("nom")} is not null
    """)
    con.execute(f"""
        create or replace temp view borme_c as
        select distinct nom, {canon("nom")} as ck, {core("nom")} as core
        from borme where {canon("nom")} is not null
    """)
    # Candidats exactes (match) i de nucli (possible).
    con.execute("""
        create or replace temp view match_exact as
        select ck, count(distinct nom) n_borme, any_value(nom) borme_nom
        from borme_c group by ck
    """)
    con.execute("""
        create or replace temp view match_core as
        select core, count(distinct nom) n_borme, any_value(nom) borme_nom
        from borme_c where length(core) >= 5 group by core
    """)
    con.execute("""
        create or replace temp view classified as
        select
            f.nom, f.import_eur, f.mercantil, f.ck, f.core,
            case when me.ck is not null then 'match'
                 when mc.core is not null then 'possible'
                 else 'no-match' end as tipus,
            coalesce(me.borme_nom, mc.borme_nom) as borme_nom,
            coalesce(me.n_borme, mc.n_borme, 0) as n_borme
        from fega_j f
        left join match_exact me on me.ck = f.ck
        left join match_core mc on mc.core = f.core and length(f.core) >= 5
    """)


def _cov(con, where: str) -> dict:
    row = con.execute(f"""
        select
            count(*) n,
            sum(import_eur) imp,
            count(*) filter (where tipus='match') n_m,
            count(*) filter (where tipus='possible') n_p,
            count(*) filter (where tipus='no-match') n_nm,
            sum(import_eur) filter (where tipus='match') imp_m,
            sum(import_eur) filter (where tipus='possible') imp_p
        from classified where {where}
    """).fetchone()
    n, imp, n_m, n_p, n_nm, imp_m, imp_p = (x or 0 for x in row)
    return {
        "n": n,
        "imp": imp,
        "n_match": n_m,
        "n_possible": n_p,
        "n_nomatch": n_nm,
        "imp_match": imp_m,
        "imp_possible": imp_p,
    }


def measure(con: duckdb.DuckDBPyConnection) -> dict:
    """Calcula l'informe de cobertura. `con` ha de tindre vistes fega/borme."""
    build_views(con)
    juridic = _cov(con, "true")
    mercantil = _cov(con, "mercantil")
    # Ambiguitat: entitats amb clau (o nucli) que casa amb > 1 empresa de BORME.
    amb = con.execute("""
        select count(*) filter (where tipus in ('match','possible')) tot,
               count(*) filter (where tipus in ('match','possible') and n_borme > 1) ambig
        from classified
    """).fetchone()
    examples = con.execute("""
        select nom, borme_nom, n_borme, round(import_eur) imp from classified
        where tipus in ('match','possible') and n_borme > 1 order by import_eur desc limit 8
    """).fetchall()
    return {
        "juridic": juridic,
        "mercantil": mercantil,
        "ambig_total": amb[0] or 0,
        "ambig_n": amb[1] or 0,
        "ambig_examples": examples,
    }


def write_sample(con: duckdb.DuckDBPyConnection, path: Path = SAMPLE_CSV, n: int = 40) -> Path:
    """Escriu una mostra de parells FEGA<->BORME (match + possible) per etiquetar a ma."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        copy (
            with m as (
                select nom as fega_nom, borme_nom, tipus, n_borme as candidats_borme,
                       ck as clau_canonica, round(import_eur) as import_eur
                from classified where tipus = 'match' order by import_eur desc limit {n // 2}
            ), p as (
                select nom as fega_nom, borme_nom, tipus, n_borme as candidats_borme,
                       ck as clau_canonica, round(import_eur) as import_eur
                from classified where tipus = 'possible' order by import_eur desc limit {n - n // 2}
            )
            select *, '' as veredicte_humà from (select * from m union all select * from p)
            order by import_eur desc
        ) to '{path.as_posix()}' (header, delimiter ',')
    """)
    return path


def _fmt(report: dict) -> str:
    j, m = report["juridic"], report["mercantil"]

    def block(title, c):
        cov_n = 100 * (c["n_match"] + c["n_possible"]) / c["n"] if c["n"] else 0
        cov_e = 100 * (c["imp_match"] + c["imp_possible"]) / c["imp"] if c["imp"] else 0
        return (
            f"\n{title}: {c['n']:,} entitats, {c['imp']:,.0f} EUR\n"
            f"  match    {c['n_match']:>6,}  ({100 * c['n_match'] / c['n']:.1f}%)  "
            f"{c['imp_match']:>14,.0f} EUR\n"
            f"  possible {c['n_possible']:>6,}  ({100 * c['n_possible'] / c['n']:.1f}%)  "
            f"{c['imp_possible']:>14,.0f} EUR\n"
            f"  no-match {c['n_nomatch']:>6,}  ({100 * c['n_nomatch'] / c['n']:.1f}%)\n"
            f"  => cobertura (match+possible): {cov_n:.1f}% entitats, {cov_e:.1f}% euros"
        )

    amb_pct = 100 * report["ambig_n"] / report["ambig_total"] if report["ambig_total"] else 0
    lines = [
        "=== SPIKE FEGA x BORME (enllac per nom) — cobertura ===",
        block("SUBCONJUNT JURIDIC (tot)", j),
        block("SUBCONJUNT MERCANTIL (elegible BORME)", m),
        f"\nAMBIGUITAT (clau casa amb >1 empresa BORME): "
        f"{report['ambig_n']:,}/{report['ambig_total']:,} ({amb_pct:.1f}%) dels matchejats",
    ]
    for nom, borme_nom, n_borme, imp in report["ambig_examples"]:
        lines.append(
            f"    {imp:>12,.0f} EUR  [{n_borme} candidats]  {nom[:40]}  ~  {borme_nom[:30]}"
        )
    return "\n".join(lines)


def load_borme(con: duckdb.DuckDBPyConnection, borme_dir: Path = BORME_DIR) -> int:
    """Carrega tots els JSONL de BORME a una taula `borme(nom, ...)`. Torna el nombre de files."""
    files = sorted(borme_dir.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(
            f"sense JSONL de BORME a {borme_dir}; executa la ingesta "
            "(python -m ingest.borme.download --start AAAA-MM-DD --end AAAA-MM-DD)"
        )
    glob = str(borme_dir / "*.jsonl")
    con.execute(
        f"create or replace temp view borme as select nom, provincia from read_json_auto('{glob}')"
    )
    return con.execute("select count(*) from borme").fetchone()[0]


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"sense {DB_PATH}; executa `just build` abans de l'spike.")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        n_borme = load_borme(con)
        n_borme_dist = con.execute(f"select count(distinct {canon('nom')}) from borme").fetchone()[
            0
        ]
        logger.info(
            "BORME: %d registres, %d empreses distintes (clau canonica)", n_borme, n_borme_dist
        )
        con.execute(
            "create or replace temp view fega as "
            "select any_value(nom_beneficiari) nom, sum(import_eur) import_eur "
            "from mart_ajudes_pac group by clau_beneficiari"
        )
        report = measure(con)
        print(_fmt(report))
        path = write_sample(con)
        print(f"\nMostra per etiquetar (match+possible barrejats): {path}")
        print(json.dumps({"borme_registres": n_borme, "borme_empreses": n_borme_dist}, indent=0))
    finally:
        con.close()


if __name__ == "__main__":
    main()
