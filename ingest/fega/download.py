"""Spike de confirmacio (Fase 0): baixa UN fitxer real de transparencia de FEGA.

NO es l'extractor de la Fase 1: nomes descarrega de forma reproduible el ZIP nacional
de beneficiaris per municipi per a un exercici, perque puguem inspeccionar-lo i validar
el contracte contracts/fega.py contra columnes reals.

Font: FEGA, dades obertes, "Datos transparencia beneficiarios por municipio". El fitxer
es nacional (totes les CCAA); el filtre a la Comunitat Valenciana es fa en inspeccio, no
en la baixada.

El ZIP es desa a data/raw/fega/ (gitignored): conte persones fisiques i no es committeja
mai. Sense claus ni secrets: es una URL publica.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.fega.download")

# URL directa del ZIP per municipi, exercici financer 2024 (16 oct 2023 - 15 oct 2024).
FEGA_2024_URL = (
    "https://www.fega.gob.es/sites/default/files/files/document/"
    "Beneficiarios_municipio_ejercicio-financiero-2024.zip"
)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "fega"


def download(url: str = FEGA_2024_URL, dest_dir: Path = RAW_DIR) -> Path:
    """Baixa el ZIP a dest_dir de forma idempotent. Torna la ruta del fitxer."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / url.rsplit("/", 1)[-1]

    if dest.exists():
        logger.info("Ja existeix, salte la baixada: %s (%d bytes)", dest, dest.stat().st_size)
        return dest

    logger.info("Baixant %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "ordit-spike/0.0 (+dades obertes)"})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (URL publica fixa)
        data = resp.read()
    dest.write_bytes(data)
    logger.info("Desat: %s (%d bytes)", dest, dest.stat().st_size)
    return dest


if __name__ == "__main__":
    download()
