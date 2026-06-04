"""Ingesta de BORME (spike de la Fase 3): llosa acotada del Registre Mercantil de la CV.

Baixa, de forma reproduible i NOMES local (build plane), els actes inscrits (BORME Seccio A)
de les tres provincies de la Comunitat Valenciana (03 Alacant, 12 Castello, 46 Valencia) per
a un rang de dates configurable, i en deixa els registres d'empresa a data/raw/borme/
(gitignored). Sense claus ni secrets: son endpoints publics de la BOE.

El BORME-A NO porta CIF; nomes el nom i el numero de full registral. Vegeu docs/sources/borme.md.

El parseig (parse_borme_a) es una funcio pura, provada amb fixtures sintetiques sense xarxa.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.borme")

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "borme"
CV_PROVINCES = ("03", "12", "46")  # Alacant, Castello, Valencia
SUMARI_URL = "https://www.boe.es/datosabiertos/api/borme/sumario/{ymd}"
_UA = {"User-Agent": "ordit-spike/0.1 (build plane local; entity-resolution viability)"}

# Cada empresa al BORME-A es un paragraf "{num full} - {RAO SOCIAL}." seguit dels actes.
_COMPANY = re.compile(r"^\s*(\d+)\s*-\s*(.+?)\.?\s*$")


def _fetch(url: str, *, as_json: bool, timeout: int = 30) -> bytes | dict:  # pragma: no cover
    """Descarrega una URL (I/O de xarxa; es verifica amb l'execucio real, no per cobertura)."""
    headers = {**_UA}
    if as_json:
        headers["Accept"] = "application/json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL publica fixa)
        data = resp.read()
    return json.loads(data) if as_json else data


def cv_items(sumari: dict) -> list[tuple[str, str, str]]:
    """Extrau els items de Seccio A (BORME-A) de les provincies CV del sumari JSON.

    Torna (font_id, codi_provincia, url_xml). Recorregut recursiu perque el JSON nia els
    items dins de diario -> sumario_diario -> seccion.
    """
    out: list[tuple[str, str, str]] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            ident = node.get("identificador", "")
            if isinstance(ident, str) and ident.startswith("BORME-A-"):
                prov = ident.split("-")[-1]
                if prov in CV_PROVINCES:
                    url_xml = node.get("url_xml")
                    url = url_xml.get("texto") if isinstance(url_xml, dict) else url_xml
                    if url:
                        out.append((ident, prov, url))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(sumari.get("data", {}).get("sumario", {}))
    return out


def parse_borme_a(
    xml_bytes: bytes, source_id: str, province_code: str, pub_date: str
) -> list[dict]:
    """Parseja un XML de BORME-A i torna un registre per empresa (funcio pura, sense xarxa)."""
    root = ET.fromstring(xml_bytes)
    records: list[dict] = []
    for p in root.iter("p"):
        text = (p.text or "").strip()
        m = _COMPANY.match(text)
        if not m:
            continue
        name = m.group(2).strip()
        if len(name) < 3:
            continue
        records.append(
            {
                "nom": name,
                "num_registre": m.group(1),
                "provincia": province_code,
                "font_id": source_id,
                "data": pub_date,
            }
        )
    return records


def download(start: dt.date, end: dt.date, dest_dir: Path = RAW_DIR) -> Path:  # pragma: no cover
    """Baixa BORME-A de la CV entre start i end (incl.) a un JSONL. Torna el cami escrit.

    Salta els dies sense edicio (404). Un registre per empresa i acte; la deduplicacio per
    nom es fa a la capa de mesura (linkage/coverage.py).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / f"borme_cv_{start:%Y%m%d}_{end:%Y%m%d}.jsonl"
    n_days = n_records = 0
    with out_path.open("w", encoding="utf-8") as fh:
        day = start
        while day <= end:
            ymd = day.strftime("%Y%m%d")
            try:
                sumari = _fetch(SUMARI_URL.format(ymd=ymd), as_json=True)
            except urllib.error.HTTPError as err:
                if err.code != 404:
                    logger.warning("sumari %s: HTTP %s", ymd, err.code)
                day += dt.timedelta(days=1)
                continue
            if not isinstance(sumari, dict) or sumari.get("status", {}).get("code") != "200":
                day += dt.timedelta(days=1)
                continue
            n_days += 1
            for source_id, prov, url in cv_items(sumari):
                try:
                    xml_bytes = _fetch(url, as_json=False)
                except urllib.error.HTTPError as err:
                    logger.warning("xml %s: HTTP %s", source_id, err.code)
                    continue
                for rec in parse_borme_a(xml_bytes, source_id, prov, day.isoformat()):
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_records += 1
            day += dt.timedelta(days=1)
    logger.info(
        "BORME CV %s..%s: %d dies, %d registres -> %s", start, end, n_days, n_records, out_path
    )
    return out_path


def _parse_args() -> argparse.Namespace:  # pragma: no cover
    ap = argparse.ArgumentParser(description="Ingesta acotada de BORME-A (CV) per a l'spike.")
    ap.add_argument("--start", required=True, help="data inicial AAAA-MM-DD")
    ap.add_argument("--end", required=True, help="data final AAAA-MM-DD (incl.)")
    return ap.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    download(dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end))
