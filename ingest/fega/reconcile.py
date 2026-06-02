"""Reconciliacio de comptes per al footgun d'ignore_errors a staging.

DuckDB llig els fitxers amb ignore_errors=true (per absorbir el ";" final nomes-2024 i
les files malformades). Aixo pot amagar silenciosament files perdudes si el format de la
font deriva. Esta reconciliacio compara les linies de dades del raw (linies - capçalera)
amb les files que DuckDB parseja de veritat (abans del filtre CV) i reporta el forat.

Si el forat creix per damunt de la tolerancia, es senyal que la font ha derivat i cal
revisar el parseig (idealment, quarantena loggejada dels rebutjos).
"""

from __future__ import annotations

from pathlib import Path

import duckdb

_CHUNK = 8 << 20

# Mateixos parametres de lectura que el model staging_fega (han d'anar sincronitzats).
_COLUMNS = {
    n: "VARCHAR"
    for n in (
        "BENEFICIARIO",
        "GRUPO_EMPRESA",
        "PROVINCIA",
        "MUNICIPIO",
        "MEDIDA",
        "OBJETIVO_ESP",
        "FEC_INI",
        "FEC_FIN",
        "FEAGA",
        "FEADER",
        "IMPORTECOFIN",
        "FEADER_COFIN",
        "IMPORTE_EUROS",
        "_trailing",
    )
}


def _count_data_lines(path: Path) -> int:
    """Compta les linies fisiques del fitxer i en lleva la capçalera."""
    newlines = 0
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            newlines += chunk.count(b"\n")
    return max(newlines - 1, 0)


def _parsed_rows(path: Path) -> int:
    sql = (
        f"select count(*) from read_csv('{path.as_posix()}', auto_detect=false, delim=';', "
        f"header=true, quote='', encoding='utf-8', columns={_COLUMNS!r}, "
        f"ignore_errors=true, null_padding=true)"
    )
    return duckdb.sql(sql).fetchone()[0]


def reconcile(utf8_path: Path) -> dict[str, int]:
    """Torna {raw_data_lines, parsed, dropped} per a un fitxer .utf8.txt."""
    raw = _count_data_lines(utf8_path)
    parsed = _parsed_rows(utf8_path)
    return {"raw_data_lines": raw, "parsed": parsed, "dropped": raw - parsed}
