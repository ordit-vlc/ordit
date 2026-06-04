"""Ingesta del Directori de Cooperatives de la Comunitat Valenciana (GVA, CC-BY).

Baixa el snapshot mes recent (2025) del directori, repara l'encoding i en deixa els
registres a data/raw/cooperatives/ (gitignored). Sense claus ni secrets: URL publica oberta.
Hi ha snapshots anuals (2020-2025); ací s'agafa el mes recent, configurable per --url.

Encoding: el CSV es UTF-8 DOBLE-CODIFICAT (mojibake de mojibake, p. ex. "VALENCIAÃˆ" per
"VALÈNCIA"). La reparacio (repair_mojibake) recupera el byte intern per caracter (cp1252,
despres latin-1) i torna a descodificar UTF-8. Funcio pura, provada amb fixtures sintetiques.

parse_csv tambe es pura: separa per ';' i torna un registre per cooperativa amb les columnes
de la font (CD_NIF, DS_RAZON_SOCIAL, ...).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.cooperatives")

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "cooperatives"
# Snapshot 2025 del directori (CC-BY). Vegeu docs/sources/cooperatives.md.
DEFAULT_URL = (
    "https://dadesobertes.gva.es/dataset/ac050833-9d08-40f5-bb7e-027db6347682/"
    "resource/e20d8485-cfd7-48e0-8ebc-a5a5bb69b230/download/cooperativas-valencianas_202501.csv"
)
_UA = {"User-Agent": "ordit/0.1 (build plane local; entity-resolution Fase 3)"}


def repair_mojibake(text: str) -> str:
    """Repara el doble-mojibake d'UTF-8: recupera el byte intern de cada caracter no-ASCII
    (cp1252, despres latin-1) i torna a descodificar UTF-8. Funcio pura."""
    out = bytearray()
    for ch in text:
        code = ord(ch)
        if code < 0x80:
            out.append(code)
            continue
        try:
            out += ch.encode("cp1252")
        except UnicodeEncodeError:
            try:
                out += ch.encode("latin-1")
            except UnicodeEncodeError:
                out += ch.encode("utf-8")
    return out.decode("utf-8", "replace")


def parse_csv(text: str) -> list[dict]:
    """Parseja el CSV (delimitat per ';') del directori. Funcio pura."""
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    records: list[dict] = []
    for row in reader:
        # Normalitza les claus (treu BOM/espais) i salta files buides.
        clean = {(k or "").strip().lstrip("﻿"): (v or "").strip() for k, v in row.items()}
        if clean.get("DS_RAZON_SOCIAL"):
            records.append(clean)
    return records


def download(url: str = DEFAULT_URL, dest_dir: Path = RAW_DIR) -> Path:  # pragma: no cover
    """Baixa el directori, repara l'encoding i escriu un JSONL. Torna el cami escrit."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (URL publica fixa)
        raw = resp.read()
    text = repair_mojibake(raw.decode("utf-8", "replace"))
    records = parse_csv(text)
    out_path = dest_dir / "cooperatives_cv.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.info("Cooperatives CV: %d registres -> %s", len(records), out_path)
    return out_path


def _parse_args() -> argparse.Namespace:  # pragma: no cover
    ap = argparse.ArgumentParser(description="Ingesta del Directori de Cooperatives de la CV.")
    ap.add_argument("--url", default=DEFAULT_URL, help="URL del CSV (per defecte, snapshot 2025)")
    return ap.parse_args()


if __name__ == "__main__":  # pragma: no cover
    args = _parse_args()
    download(args.url)
