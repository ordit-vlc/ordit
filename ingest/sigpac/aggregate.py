"""Agrega els recintes SIGPAC a superficie per municipi i us (memory-safe).

L'entrada (els .7z de recintes per provincia, vegeu download.py) son milions de poligons:
1.085.000 nomes a Alacant. Carregar-los sencers esgotaria la memoria del build plane
(ROADMAP No-go de la Fase 2). Per aixo NO toquem la geometria: GDAL llig nomes la taula
d'atributs del SHP dins del .7z (via /vsi7z/) i agrega amb el dialecte SQLITE en STREAMING.
Pic mesurat: ~200 MiB de RSS per provincia (vs diversos GB si carregarem la geometria).

Sortida: un sol CSV compacte (~milers de files) a data/raw/sigpac/, que la capa staging
de dbt consumeix. Una fila per (codi de municipi de catastro, us SIGPAC, grup de cultiu)
amb el recompte de recintes i la superficie total en m2.

Reproduir:
    uv run python -m ingest.sigpac.download    # baixa els tres .7z
    uv run python -m ingest.sigpac.aggregate   # genera recintos_agg_<campanya>.csv
"""

from __future__ import annotations

import csv
import logging
import subprocess
from pathlib import Path

from ingest.sigpac.download import CAMPAIGN, PROVINCES, RAW_DIR, _filename

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.sigpac.aggregate")

OUT = RAW_DIR / f"recintos_agg_{CAMPAIGN}.csv"
FIELDNAMES = ("catastro_code", "uso_sigpac", "grupo_cult", "n_recintes", "surface_m2")

# Agregacio atribut-only: codi de municipi de catastro (provincia 2 + municipi 3, zero-pad)
# x us SIGPAC x grup de cultiu -> recompte + superficie en m2. Sense geometria.
_SQL = (
    "SELECT printf('%02d%03d', PROVINCIA, MUNICIPIO) AS catastro_code, "
    "USO_SIGPAC AS uso_sigpac, GRUPO_CULT AS grupo_cult, "
    "COUNT(*) AS n_recintes, ROUND(SUM(DN_SURFACE), 2) AS surface_m2 "
    "FROM RECINTO GROUP BY catastro_code, USO_SIGPAC, GRUPO_CULT"
)


def _aggregate_province(province: str, raw_dir: Path) -> list[dict[str, str]]:
    """Agrega un .7z de provincia a files de (catastro_code, us, grup) via ogr2ogr."""
    src = f"/vsi7z/{(raw_dir / _filename(province)).as_posix()}"
    logger.info("Agregant provincia %s (%s)", province, src)
    # ogr2ogr escriu el CSV a stdout (/vsistdout/) per a no deixar fitxers temporals.
    result = subprocess.run(
        ["ogr2ogr", "-f", "CSV", "/vsistdout/", src, "-dialect", "SQLITE", "-sql", _SQL],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = list(csv.DictReader(result.stdout.splitlines()))
    logger.info("  %s: %d combinacions (municipi x us x grup)", province, len(rows))
    return rows


def aggregate(raw_dir: Path = RAW_DIR, out: Path = OUT) -> Path:
    """Agrega les tres provincies a un sol CSV. Torna la ruta de sortida."""
    all_rows: list[dict[str, str]] = []
    for province in PROVINCES:
        all_rows.extend(_aggregate_province(province, raw_dir))
    all_rows.sort(key=lambda r: (r["catastro_code"], r["uso_sigpac"], r["grupo_cult"] or ""))

    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)
    total_ha = sum(float(r["surface_m2"]) for r in all_rows) / 10_000
    logger.info("Escrit %s: %d files, %.0f ha totals", out, len(all_rows), total_ha)
    return out


if __name__ == "__main__":
    aggregate()
