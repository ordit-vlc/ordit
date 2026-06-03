"""Construeix els seeds de geografia i resol els codis postals de FEGA a municipi INE.

Genera tres seeds a ordit_dbt/seeds/ (vegeu docs/sources/geografia.md):
  - dim_municipi.csv     : codi_ine, nom (valencia), comarca, provincia (542 municipis CV).
  - xwalk_cp_ine.csv     : postal_code -> codi_ine (via 1, GeoNames CC-BY 4.0).
  - xwalk_locality.csv   : municipi_raw (la cadena de FEGA) -> codi_ine + resolved_by.

Resolucio en DUES VIES que es validen mutuament:
  via 1  CP -> codi_ine pel crosswalk de GeoNames.
  via 2  nom oficial (valencia GVA + castella/local INE via GeoNames) amb maneig de
         bilingue "X/Y" i de truncament (prefix unic).
Quan ambdues resolen han de COINCIDIR; si discrepen, es 'discrepancy' i queda sense
municipi (default-deny: no s'inventa cap municipi). El que no resol cap via queda
'unresolved'.

Entrades (al build plane, gitignored): data/raw/geo/municipis-VAL.json (atributs del
GeoJSON de TopQuaranta) i data/raw/geonames/ES.txt (GeoNames). El cross-check de noms usa
poblacio-valenciana (CC0) si el clon es accessible.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.geo.build_seeds")

ROOT = Path(__file__).resolve().parents[2]
GEOJSON = ROOT / "data" / "raw" / "geo" / "municipis-VAL.json"
GEONAMES = ROOT / "data" / "raw" / "geonames" / "ES.txt"
DB_PATH = ROOT / "data" / "ordit.duckdb"
SEEDS = ROOT / "ordit_dbt" / "seeds"
# Cross-check opcional de noms contra poblacio-valenciana (CC0). Ruta del clon via entorn;
# si no s'indica o no existeix, el cross-check se salta (no es bloquejant).
POBLACIO = Path(os.environ.get("ORDIT_POBLACIO_CSV", ""))

PROVINCIA = {"03": "Alacant", "12": "Castelló", "46": "València"}


def _norm(s: str) -> str:
    """Normalitza un nom per a comparar: sense accents, minuscules, sense article."""
    s = unicodedata.normalize("NFKD", s.strip().lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"^(l'|el |la |els |les |l’)", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _load_dim() -> tuple[dict, dict]:
    """dim_municipi des del GeoJSON. Torna (rows_per_ine, name_norm -> {ine})."""
    feats = json.loads(GEOJSON.read_text(encoding="utf-8"))["features"]
    dim, name2ine = {}, defaultdict(set)
    for f in feats:
        p = f["properties"]
        ine = p["codi_ine"]
        dim[ine] = {
            "codi_ine": ine,
            "nom": p["municipi"],
            "comarca": p["comarca"],
            "provincia": PROVINCIA.get(ine[:2], ""),
        }
        name2ine[_norm(p["municipi"])].add(ine)
    return dim, name2ine


def _load_geonames(ine_set: set[str]) -> tuple[dict, dict]:
    """GeoNames. Torna (cp -> {ine}, name_norm -> {ine}) restringit als INE de la CV."""
    cp2ine, gname2ine = defaultdict(set), defaultdict(set)
    for line in GEONAMES.read_text(encoding="utf-8").splitlines():
        c = line.split("\t")
        if len(c) < 9 or c[8] not in ine_set:
            continue
        cp, place, adm3 = c[1], c[2], c[7]
        cp2ine[cp].add(c[8])
        for nm in (place, adm3):
            if nm:
                gname2ine[_norm(nm)].add(c[8])
    return cp2ine, gname2ine


def _single(s: set[str]) -> str | None:
    return next(iter(s)) if len(s) == 1 else None


def main() -> None:
    dim, name2ine = _load_dim()
    ine_set = set(dim)
    cp2ine, gname2ine = _load_geonames(ine_set)
    logger.info("dim_municipi: %d INE | xwalk CP: %d", len(dim), len(cp2ine))

    # Alies de nom (via 2): valencia (GeoJSON) + castella/local (GeoNames), nomes els
    # noms normalitzats que apunten a un unic INE.
    alias = defaultdict(set)
    for nn, ines in list(name2ine.items()) + list(gname2ine.items()):
        alias[nn] |= ines
    alias = {nn: _single(ines) for nn, ines in alias.items() if _single(ines)}
    alias_norms = list(alias)

    def resolve_name(locality: str) -> str | None:
        cands = set()
        for part in re.split(r"\s*/\s*", locality):
            nn = _norm(part)
            if nn in alias:
                cands.add(alias[nn])
        if not cands:  # truncament: prefix unic d'un nom oficial
            nn = _norm(locality)
            if len(nn) >= 5:
                pref = {alias[a] for a in alias_norms if a.startswith(nn)}
                if _single(pref):
                    cands.add(_single(pref))
        return _single(cands)

    # Resol cada localitat distinta de FEGA. Llig staging_fega (NO l'intermediate int_fega):
    # l'intermediate ja depen del seed xwalk_locality que generem ací, i llegir-lo crearia
    # una dependencia circular. staging_fega nomes depen del raw.
    con = duckdb.connect(str(DB_PATH), read_only=True)
    pairs = con.sql(
        "select municipality, count(*) n from staging_fega "
        "where municipality is not null group by 1"
    ).fetchall()

    loc_rows = []
    stat = defaultdict(int)
    rowstat = defaultdict(int)
    many_to_one = sum(1 for s in cp2ine.values() if len(s) > 1)
    for raw, n in pairs:
        m = re.match(r"\s*(\d{5})\s*-\s*(.+)$", raw)
        if not m:
            loc_rows.append((raw, "", "unresolved"))
            stat["unresolved"] += 1
            rowstat["unresolved"] += n
            continue
        cp, loc = m.group(1), m.group(2)
        cp_ine = _single(cp2ine.get(cp, set()))
        name_ine = resolve_name(loc)
        if cp_ine and name_ine:
            by, ine = ("both", cp_ine) if cp_ine == name_ine else ("discrepancy", "")
        elif cp_ine:
            by, ine = "cp", cp_ine
        elif name_ine:
            by, ine = "name", name_ine
        else:
            by, ine = "unresolved", ""
        loc_rows.append((raw, ine, by))
        stat[by] += 1
        rowstat[by] += n

    # Cross-check de noms vs poblacio-valenciana (CC0).
    pob_warn = ""
    if POBLACIO.is_file():
        pob = {_norm(r[0]) for r in csv.reader(POBLACIO.open(encoding="utf-8")) if r}
        missing = sum(1 for ine in dim if _norm(dim[ine]["nom"]) not in pob)
        pob_warn = f" | noms dim sense match a poblacio (CC0): {missing}/{len(dim)}"

    # Escriu els seeds.
    SEEDS.mkdir(parents=True, exist_ok=True)
    with (SEEDS / "dim_municipi.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["codi_ine", "nom", "comarca", "provincia"])
        for ine in sorted(dim):
            d = dim[ine]
            w.writerow([d["codi_ine"], d["nom"], d["comarca"], d["provincia"]])
    with (SEEDS / "xwalk_cp_ine.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["postal_code", "codi_ine"])
        for cp in sorted(cp2ine):
            ine = _single(cp2ine[cp])
            if ine:
                w.writerow([cp, ine])
    with (SEEDS / "xwalk_locality.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["municipi_raw", "codi_ine", "resolved_by"])
        for raw, ine, by in sorted(loc_rows):
            w.writerow([raw, ine, by])

    # Informe de cobertura.
    tot = sum(rowstat.values())
    resolt = rowstat["both"] + rowstat["cp"] + rowstat["name"]
    logger.info("=== COBERTURA (files CV: %d) ===", tot)
    for k in ("both", "cp", "name", "discrepancy", "unresolved"):
        pct = rowstat[k] * 100 // tot
        logger.info("  %-11s files %8d (%2d%%) | localitats %d", k, rowstat[k], pct, stat[k])
    logger.info(
        "  >> RESOLT %d (%d%%) | CP many-to-one: %d%s",
        resolt,
        resolt * 100 // tot,
        many_to_one,
        pob_warn,
    )


if __name__ == "__main__":
    main()
