"""Extrau la geometria dels municipis de la Comunitat Valenciana per a l'explorador.

Font: GISCO/Eurostat LAU 2021 (EPSG:4326, 1:1M), derivat de l'EuroBoundaryMap
d'EuroGeographics (per a Espanya, font nacional IGN). LAU_ID = codi INE de municipi.
Llicencia: reutilitzacio amb atribucio "© EuroGeographics". Vegeu docs/sources/geografia.md.

Filtra els 542 municipis de la CV, enllaça nom i comarca per codi_ine des del seed
dim_municipi, simplifica les coordenades (arrodonint, sense llibreria geoespacial) i escriu
un GeoJSON compacte a explorer/geo/. Sense dissoldre a comarca: l'explorador acoloreix els
poligons municipals segons l'agregat de comarca o de municipi (la coropleta de comarca
NO necessita fusionar geometries).

Entrada (build plane, gitignored): data/raw/geo/LAU_2021_EU.geojson
  (https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/LAU_RG_01M_2021_4326.geojson).
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.geo.build_geometry")

ROOT = Path(__file__).resolve().parents[2]
LAU = ROOT / "data" / "raw" / "geo" / "LAU_2021_EU.geojson"
DIM = ROOT / "ordit_dbt" / "seeds" / "dim_municipi.csv"
OUT = ROOT / "explorer" / "geo" / "municipis-cv.geojson"

_NDIGITS = 4  # ~11 m; sobrat per a un mapa estilitzat


def _round_ring(ring: list) -> list:
    """Arrodoneix les coordenades i elimina punts consecutius identics."""
    out = []
    for x, y in ring:
        p = [round(x, _NDIGITS), round(y, _NDIGITS)]
        if not out or out[-1] != p:
            out.append(p)
    return out


def _simplify(geom: dict) -> dict:
    t = geom["type"]
    if t == "Polygon":
        return {"type": t, "coordinates": [_round_ring(r) for r in geom["coordinates"]]}
    if t == "MultiPolygon":
        return {
            "type": t,
            "coordinates": [[_round_ring(r) for r in poly] for poly in geom["coordinates"]],
        }
    return geom


def main() -> None:
    dim = {
        r["codi_ine"]: (r["nom"], r["comarca"]) for r in csv.DictReader(DIM.open(encoding="utf-8"))
    }
    eu = json.loads(LAU.read_text(encoding="utf-8"))["features"]
    feats = []
    for f in eu:
        p = f["properties"]
        ine = str(p.get("LAU_ID", ""))
        if p.get("CNTR_CODE") != "ES" or ine not in dim:
            continue
        nom, comarca = dim[ine]
        feats.append(
            {
                "type": "Feature",
                "properties": {"codi_ine": ine, "municipi": nom, "comarca": comarca},
                "geometry": _simplify(f["geometry"]),
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    logger.info("Escrit %s: %d municipis (%d KiB)", OUT, len(feats), OUT.stat().st_size >> 10)


if __name__ == "__main__":
    main()
