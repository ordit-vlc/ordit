"""Ingesta de FEGA: baixa els fitxers reals de transparencia de beneficiaris.

Baixa de forma reproduible el ZIP nacional de beneficiaris per municipi per als exercicis
recents disponibles i en deixa el .txt descomprimit a data/raw/fega/ (gitignored: conte
persones fisiques, no es committeja mai). Sense claus ni secrets: son URL publiques.

El raw es manté SENCER (totes les CCAA, totes les persones); el filtre a la Comunitat
Valenciana es fa a la capa de models (staging), no ací. Mode privat: cap filtre per tipus
d'entitat (vegeu CLAUDE.md §8).

Els noms de fitxer de la font no son consistents entre anys (guio vs guio baix entre
"ejercicio" i "financiero"), per aixo es mapegen explicitament per exercici.
"""

from __future__ import annotations

import logging
import re
import urllib.request
import zipfile
from pathlib import Path

# El fitxer de la font es d'encoding MIXT: majoritariament latin-1 (un byte per
# caracter, p. ex. "a" amb accent greu = 0xE0), pero alguns camps ja venen en UTF-8
# (p. ex. "I" amb accent agut = 0xC3 0x8D). DuckDB no el llig directament, aixi que
# l'ingest el normalitza a UTF-8 net (pas tecnic, sense filtrar res: el raw segueix
# sencer). Staging consumeix el fitxer .utf8.txt.
#
# Normalitzacio en dos passos, NO una transcodificacio cega:
#   1. Descodifica com a latin-1: lossless, cap byte es perd (cp1252 perdia 0x8D).
#   2. Repara el mojibake d'UTF-8 mal interpretat: nomes les subcadenes que formen una
#      seqüencia UTF-8 valida es reinterpreten; la resta (latin-1) es respecta.
# Es l'equivalent dirigit del que faria ftfy, sense dependencia nova.
_UTF8_SEQUENCE = re.compile(
    "[\xc2-\xdf][\x80-\xbf]"  # 2 bytes
    "|[\xe0-\xef][\x80-\xbf]{2}"  # 3 bytes
    "|[\xf0-\xf4][\x80-\xbf]{3}"  # 4 bytes
)

# Especials de CP1252 al rang C1 (0x80-0x9F): en descodificar latin-1 queden com a
# codepoints de control; els tornem al seu caracter previst (cometes tipografiques,
# guions...), com fa ftfy. Els bytes indefinits a CP1252 es respecten tal qual.
_CP1252_C1 = {
    cp: bytes([cp]).decode("cp1252")
    for cp in range(0x80, 0xA0)
    if bytes([cp]).decode("cp1252", errors="ignore")
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.fega.download")


def _repair_utf8(match: re.Match[str]) -> str:
    """Reinterpreta una seqüencia latin-1 que de fet era UTF-8 (mojibake)."""
    try:
        return match.group(0).encode("latin-1").decode("utf-8")
    except UnicodeDecodeError:
        return match.group(0)


def decode_mixed(raw: bytes) -> str:
    """Descodifica bytes d'encoding mixt latin-1 + UTF-8 sense perdre cap byte.

    "AGR\\xc3\\x8dCOLA" (Í en UTF-8) -> "AGRICOLA" amb accent; "Alm\\xe0..." (latin-1)
    es respecta. Operar per linies garanteix que cap seqüencia UTF-8 quede partida (els
    bytes UTF-8 son tots >= 0x80, mai un salt de linia).
    """
    repaired = _UTF8_SEQUENCE.sub(_repair_utf8, raw.decode("latin-1"))
    return repaired.translate(_CP1252_C1)


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
    """Reescriu el .txt (encoding mixt) com a UTF-8 net en un .utf8.txt germa.

    Idempotent. Processa per linies: cap seqüencia UTF-8 queda partida (els bytes UTF-8
    son tots >= 0x80, mai un salt de linia), aixi que la reparacio del mojibake es segura.
    """
    utf8_path = txt_path.with_suffix(".utf8.txt")
    if utf8_path.exists() and utf8_path.stat().st_mtime >= txt_path.stat().st_mtime:
        logger.info("UTF-8 ja existeix, salte la normalitzacio: %s", utf8_path)
        return utf8_path
    logger.info("Normalitzant encoding mixt latin-1/UTF-8 -> UTF-8: %s", utf8_path)
    with txt_path.open("rb") as src, utf8_path.open("w", encoding="utf-8", newline="") as dst:
        for raw_line in src:
            dst.write(decode_mixed(raw_line))
    return utf8_path


def download(dest_dir: Path = RAW_DIR) -> list[Path]:
    """Baixa i normalitza tots els exercicis disponibles. Torna les rutes dels .utf8.txt."""
    return [_download_one(year, url, dest_dir) for year, url in sorted(EXERCISES.items())]


if __name__ == "__main__":
    paths = download()
    logger.info("Fitxers raw (UTF-8) disponibles: %s", [str(p) for p in paths])
