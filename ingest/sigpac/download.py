"""Ingesta de SIGPAC: baixa la capa de recintes de la Comunitat Valenciana (ICV).

Baixa de forma reproduible i idempotent els fitxers SHP comprimits (.7z) de recintes
SIGPAC per provincia (Alacant, Castello, Valencia) a data/raw/sigpac/ (gitignored). Sense
claus ni secrets: son URL publiques de l'ICV. Llicencia CC-BY (vegeu docs/sources/sigpac.md).

El raw es manté SENCER (els tres .7z sencers, totes les parcel.les): el filtre i
l'agregacio a superficie per municipi es fan aigües avall (vegeu aggregate.py i la capa de
models). El .7z NO es descomprimeix a disc: GDAL el llig directament via /vsi7z/ (GDAL
>= 3.7), aixi no cal cap binari de 7z ni duplicar ~3 GB de SHP descomprimit.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.sigpac.download")

# Exercici (campanya) SIGPAC objectiu. La campanya 2025 (dades a 10-01-2025) casa amb
# l'exercici FEGA mes recent. El codi de recurs de l'ICV ("0050") es estable entre anys.
CAMPAIGN = 2025
_BASE = f"https://descargas.icv.gva.es/dcd/14_mediorural/03_pac/{CAMPAIGN}_SIGPAC_0050"

# Codi de provincia de l'ICV -> codi INE de provincia. Nomes recintes (no parcel.les: per a
# la superficie per us, el recinte es la unitat amb us del sol assignat).
PROVINCES: dict[str, str] = {"PALI": "03", "PCAS": "12", "PVAL": "46"}

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "sigpac"


def _filename(province: str) -> str:
    return f"1403_{CAMPAIGN}{province}_SIGPAC_RECINTOS_25830_SHP.7z"


def _download_one(province: str, dest_dir: Path) -> Path:
    """Baixa UN .7z de recintes de forma idempotent. Torna la ruta del fitxer."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = _filename(province)
    url = f"{_BASE}/{name}"
    dest = dest_dir / name

    if dest.exists():
        logger.info("7z ja existeix, salte la baixada: %s", dest)
        return dest

    logger.info("Baixant recintes de %s: %s", province, url)
    req = urllib.request.Request(url, headers={"User-Agent": "ordit/0.0 (+dades obertes)"})
    with urllib.request.urlopen(req, timeout=600) as resp:  # noqa: S310 (URL publica fixa)
        dest.write_bytes(resp.read())
    logger.info("Desat: %s (%d bytes)", dest, dest.stat().st_size)
    return dest


def download(dest_dir: Path = RAW_DIR) -> list[Path]:
    """Baixa els recintes de les tres provincies de la CV. Torna les rutes dels .7z."""
    return [_download_one(p, dest_dir) for p in PROVINCES]


if __name__ == "__main__":
    paths = download()
    logger.info("Fitxers raw SIGPAC disponibles: %s", [str(p) for p in paths])
