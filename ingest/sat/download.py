"""Ingesta del Registre de SAT de la Comunitat Valenciana (GVA, CC-BY).

Baixa el directori (CSV, ambit autonomic valencia) i en deixa els registres a
data/raw/sat/ (gitignored). Sense claus ni secrets: URL publica oberta.

Encoding: el CSV es UTF-8 NET (a diferencia del de cooperatives, que ve doble-codificat);
es descodifica directament. Hi ha ~1 registre malformat (vegeu docs/sources/sat.md), tolerat.

parse_csv es una funcio pura, provada amb fixtures sintetiques sense xarxa.
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
logger = logging.getLogger("ingest.sat")

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "sat"
DEFAULT_URL = (
    "https://dadesobertes.gva.es/dataset/78fff61b-22db-42b7-ba17-adf7f22bcbd5/"
    "resource/35931fc5-54a5-48cb-953c-3051258acade/download/"
    "registro-de-sat-de-la-comunidad-valenciana-.csv"
)
_UA = {"User-Agent": "ordit/0.1 (build plane local; entity-resolution Fase 3)"}


def parse_csv(text: str) -> list[dict]:
    """Parseja el CSV (delimitat per ';') del directori de SAT. Funcio pura.

    Normalitza les claus (treu BOM/espais) i salta les files sense denominacio.
    """
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    records: list[dict] = []
    for row in reader:
        clean = {(k or "").strip().lstrip("﻿"): (v or "").strip() for k, v in row.items()}
        if clean.get("DENOMINACIÓN") and clean.get("Nº REGISTRO"):
            records.append(clean)
    return records


def download(url: str = DEFAULT_URL, dest_dir: Path = RAW_DIR) -> Path:  # pragma: no cover
    """Baixa el directori (UTF-8 net) i escriu un JSONL. Torna el cami escrit."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (URL publica fixa)
        raw = resp.read()
    records = parse_csv(raw.decode("utf-8", "replace"))
    out_path = dest_dir / "sat_cv.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.info("SAT CV: %d registres -> %s", len(records), out_path)
    return out_path


def _parse_args() -> argparse.Namespace:  # pragma: no cover
    ap = argparse.ArgumentParser(description="Ingesta del Registre de SAT de la CV.")
    ap.add_argument("--url", default=DEFAULT_URL, help="URL del CSV (per defecte, el directori CV)")
    return ap.parse_args()


if __name__ == "__main__":  # pragma: no cover
    args = _parse_args()
    download(args.url)
