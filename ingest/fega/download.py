"""Ingesta de FEGA: baixa els fitxers reals de transparencia de beneficiaris.

Baixa de forma reproduible el ZIP nacional de beneficiaris per municipi per als exercicis
recents disponibles i en deixa el .txt descomprimit a data/raw/fega/ (gitignored: conte
persones fisiques, no es committeja mai). Sense claus ni secrets: son URL publiques.

El raw es manté SENCER (totes les CCAA, totes les persones); el filtre a la Comunitat
Valenciana i la classificacio juridica/fisica es fan a la capa de models (staging i
marts), no ací. Vegeu DATA-PROTECTION.md.

Els noms de fitxer de la font no son consistents entre anys (guio vs guio baix entre
"ejercicio" i "financiero"), per aixo es mapegen explicitament per exercici.
"""

from __future__ import annotations

import logging
import urllib.request
import zipfile
from pathlib import Path

# El fitxer de la font es Windows-1252 (latin-1 amb bytes CP1252 dispersos: cometa
# tipografica 0x91 i algun byte de control). DuckDB no el llig directament, aixi que
# l'ingest el normalitza a UTF-8 (pas tecnic, sense filtrar ni classificar res: el raw
# segueix sencer). Staging consumeix el fitxer .utf8.txt.
_SOURCE_ENCODING = "cp1252"
_CHUNK = 8 << 20  # 8 MiB; CP1252 es d'un sol byte, partir per blocs es segur

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.fega.download")

_BASE = "https://www.fega.gob.es/sites/default/files/files/document"

# Exercici financer -> URL directa del ZIP per municipi. Nomes els exercicis disponibles
# (la font els manté consultables 2 anys). Confirmat amb HEAD el 2026-06-02.
EXERCISES: dict[int, str] = {
    2024: f"{_BASE}/Beneficiarios_municipio_ejercicio-financiero-2024.zip",
    2025: f"{_BASE}/Beneficiarios_municipio_ejercicio_financiero-2025.zip",
}

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "fega"


def _download_one(year: int, url: str, dest_dir: Path) -> Path:
    """Baixa i descomprimeix UN exercici de forma idempotent. Torna la ruta del .txt."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / url.rsplit("/", 1)[-1]

    if not zip_path.exists():
        logger.info("Baixant exercici %d: %s", year, url)
        req = urllib.request.Request(url, headers={"User-Agent": "ordit/0.0 (+dades obertes)"})
        with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310 (URL publica fixa)
            zip_path.write_bytes(resp.read())
        logger.info("Desat ZIP: %s (%d bytes)", zip_path, zip_path.stat().st_size)
    else:
        logger.info("ZIP ja existeix, salte la baixada: %s", zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        member = zf.namelist()[0]
        txt_path = dest_dir / member
        if not txt_path.exists():
            logger.info("Descomprimint %s -> %s", member, txt_path)
            zf.extract(member, dest_dir)
        else:
            logger.info("TXT ja existeix, salte la descompressio: %s", txt_path)
    return _normalize_encoding(txt_path)


def _normalize_encoding(txt_path: Path) -> Path:
    """Reescriu el .txt (CP1252) com a UTF-8 en un .utf8.txt germa, de forma idempotent."""
    utf8_path = txt_path.with_suffix(".utf8.txt")
    if utf8_path.exists() and utf8_path.stat().st_mtime >= txt_path.stat().st_mtime:
        logger.info("UTF-8 ja existeix, salte la normalitzacio: %s", utf8_path)
        return utf8_path
    logger.info("Normalitzant encoding CP1252 -> UTF-8: %s", utf8_path)
    with txt_path.open("rb") as src, utf8_path.open("w", encoding="utf-8", newline="") as dst:
        while chunk := src.read(_CHUNK):
            dst.write(chunk.decode(_SOURCE_ENCODING, errors="replace"))
    return utf8_path


def download(dest_dir: Path = RAW_DIR) -> list[Path]:
    """Baixa i normalitza tots els exercicis disponibles. Torna les rutes dels .utf8.txt."""
    return [_download_one(year, url, dest_dir) for year, url in sorted(EXERCISES.items())]


if __name__ == "__main__":
    paths = download()
    logger.info("Fitxers raw (UTF-8) disponibles: %s", [str(p) for p in paths])
