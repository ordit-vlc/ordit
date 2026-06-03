"""Construeix el crosswalk codi de municipi de catastro -> codi INE per a la CV.

El codi de municipi de SIGPAC/Catastro (DGC) NO coincideix amb el codi INE per a 210 dels
542 municipis de la Comunitat Valenciana: hi ha un desfasament sistematic a la provincia de
Valencia i codis especials per a capitals i municipis segregats (p. ex. catastro 46066 =
Beniparrell, pero INE 46065). Unir per igualtat directa assignaria silenciosament la
superficie al municipi equivocat. Per aixo cal el crosswalk oficial.

Font: FEGA, "Relacion de municipios por CCAA con equivalencias entre los codigos INE y
Catastro" (campanya 2026), full "RELACION MUNCIPIOS SIGPAC", columnes "Municipio INE" i
"Municipio" (catastro). Vegeu docs/sources/sigpac.md. Entrada al build plane (gitignored):
data/raw/catastro_ine/RELACION_MUNICIPIOS_INE_CATASTRO_2026.xlsx

Sortida (committejada, sense dades personals): ordit_dbt/seeds/xwalk_catastro_ine.csv amb
catastro_code -> codi_ine per als 542 municipis de la CV (provincies 03, 12, 46).
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import openpyxl

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.sigpac.build_crosswalk")

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "raw" / "catastro_ine" / "RELACION_MUNICIPIOS_INE_CATASTRO_2026.xlsx"
OUT = ROOT / "ordit_dbt" / "seeds" / "xwalk_catastro_ine.csv"
CV_PROVINCES = (3, 12, 46)  # Alacant, Castello, Valencia


def build(src: Path = SRC, out: Path = OUT) -> Path:
    """Llig l'Excel de FEGA i escriu el crosswalk catastro -> INE de la CV."""
    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    ws = wb["RELACION MUNCIPIOS SIGPAC"]
    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    col = {name: i for i, name in enumerate(header)}

    seen: dict[str, str] = {}  # catastro_code -> codi_ine (dedup: el full porta files per zona)
    for r in rows:
        province = r[col["Provincia"]]
        if province not in CV_PROVINCES:
            continue
        catastro_code = f"{province:02d}{int(r[col['Municipio']]):03d}"
        codi_ine = f"{province:02d}{int(r[col['Municipio INE']]):03d}"
        seen[catastro_code] = codi_ine

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["catastro_code", "codi_ine"])
        writer.writerows(sorted(seen.items()))
    n_diff = sum(1 for c, i in seen.items() if c != i)
    logger.info("Escrit %s: %d municipis CV (%d amb catastro != INE)", out, len(seen), n_diff)
    return out


if __name__ == "__main__":
    build()
