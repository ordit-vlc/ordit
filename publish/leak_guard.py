"""Guard de fuga: cap dada de persona física pot eixir del build plane.

Gate #5 estés a TOT el que es committeja o es serveix (data/dist, seeds publicables, el
Parquet de l'explorador). Verifica que un artefacte conté 0 marcadors de persona física:

  - cap codi anònim de FEGA (`ES#NNNNNNNN`),
  - (per al mart) cap beneficiari amb `entity_type != 'legal'` segons l'intermediate,
  - extensió Fase 3: cap nom d'administrador del BORME (vegeu BORME_MARKERS).

És el que permet construir sense por: la frontera build → serve queda comprovada
automàticament (a CI i a `just publish`). Vegeu DATA-PROTECTION.md §6-§7.
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb

# Codi anònim de persona física de FEGA: "ES#" seguit de dígits.
PHYSICAL_CODE = re.compile(r"ES#\d")
# Extensió Fase 3: marcadors de noms d'administrador del BORME (encara cap).
BORME_MARKERS: tuple[re.Pattern[str], ...] = ()


class LeakError(Exception):
    """Un artefacte que ix del build plane conté dades de persona física."""


def scan_text_artifact(path: Path) -> list[str]:
    """Torna els fragments d'un fitxer de text (CSV, GeoJSON…) amb marcadors físics."""
    hits: list[str] = []
    patterns = (PHYSICAL_CODE, *BORME_MARKERS)
    with path.open(encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            for pat in patterns:
                if pat.search(line):
                    hits.append(f"{path.name}:{i}: {line.strip()[:120]}")
                    break
    return hits


def assert_text_artifact_clean(path: Path) -> None:
    hits = scan_text_artifact(path)
    if hits:
        raise LeakError(f"fuga de dades de persona física a {path}:\n  " + "\n  ".join(hits[:10]))


def mart_parquet_violations(
    con: duckdb.DuckDBPyConnection, parquet_path: Path, intermediate: str = "int_fega_classified"
) -> dict[str, int]:
    """Compta marcadors físics al Parquet d'un mart: codis ES# i files no 'legal'."""
    p = parquet_path.as_posix()
    es = con.execute(
        f"select count(*) from read_parquet('{p}') "
        "where regexp_matches(nom_beneficiari, 'ES#[0-9]')"
    ).fetchone()[0]
    # Cada beneficiari publicat ha de ser 'legal' a l'intermediate (cross-check de gate #5).
    nonlegal = con.execute(
        f"""
        select count(*) from read_parquet('{p}') p
        where not exists (
            select 1 from {intermediate} i
            where i.beneficiary_name = p.nom_beneficiari and i.entity_type = 'legal'
        )
        """
    ).fetchone()[0]
    return {"es_codes": es, "non_legal": nonlegal}


def assert_mart_parquet_clean(
    con: duckdb.DuckDBPyConnection, parquet_path: Path, intermediate: str = "int_fega_classified"
) -> None:
    v = mart_parquet_violations(con, parquet_path, intermediate)
    if v["es_codes"] or v["non_legal"]:
        raise LeakError(
            f"fuga al Parquet {parquet_path.name}: {v['es_codes']} codis ES#, "
            f"{v['non_legal']} files no 'legal'. NO es pot publicar ni servir."
        )
