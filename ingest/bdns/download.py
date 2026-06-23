"""Ingesta de BDNS: baixa les concessions reals de subvencions per a la Comunitat Valenciana.

La BDNS (Base de Datos Nacional de Subvenciones) publica TOTES les subvencions publiques
espanyoles a nivell d'entitat, amb API JSON oberta. A diferencia de FEGA, cada concessio
porta el NIF/CIF del beneficiari (incrustat al camp `beneficiario`), cosa que la fa l'eix
natural per a guanyar identificador fort. Vegeu docs/sources/bdns.md.

Sense claus ni secrets: l'API es publica. El raw es manté SENCER (totes les concessions de
la regio, incloent persones fisiques anonimitzades en origen amb `*`); cap filtre ací. Mode
privat (CLAUDE.md §8): el raw viu a data/raw/bdns/ (gitignored), mai a git ni a CI.

L'API torna pagines de fins a 10.000 registres (`content`), amb metadades de paginacio
(`totalPages`, `totalElements`). Es desa un fitxer JSONL per (regio, any), una concessio per
linia, per a un staging reproduible.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest.bdns.download")

# API publica del SNPSAP/BDNS (sense clau). vpd=GE es el portal general.
BDNS_API_BASE = "https://www.infosubvenciones.es/bdnstrans/api"
CONCESIONES_BUSQUEDA = f"{BDNS_API_BASE}/concesiones/busqueda"

# Identificador de regio de la Comunitat Valenciana (NUTS ES52) a l'API /regiones.
REGIO_COMUNITAT_VALENCIANA = 54

PAGE_SIZE = 1000  # maxim de l'API: 10000; 1000 es prudent i estable.
USER_AGENT = "ordit-bdns/0.1 (+https://github.com/ordit-vlc/ordit)"
_PAUSA_S = 0.5  # cortesia entre pagines, per no martellejar l'API publica.


def _fetch_page(regio: int, any_: int, page: int) -> dict:
    """Baixa una pagina de concessions per a una regio i un any (fechaConcesion DD/MM/YYYY)."""
    params = {
        "vpd": "GE",
        "pageSize": PAGE_SIZE,
        "page": page,
        "regiones": regio,
        "fechaDesde": f"01/01/{any_}",
        "fechaHasta": f"31/12/{any_}",
        "order": "fechaConcesion",
        "direccion": "asc",
    }
    url = f"{CONCESIONES_BUSQUEDA}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (URL fixa i https)
        return json.loads(resp.read().decode("utf-8"))


def download_any(
    any_: int,
    regio: int = REGIO_COMUNITAT_VALENCIANA,
    dest_dir: Path | None = None,
) -> Path:
    """Baixa totes les concessions d'un any per a una regio i les desa com a JSONL.

    Torna el cami del fitxer escrit. Una concessio per linia (camps de la font tal qual).
    """
    dest_dir = dest_dir or Path("data/raw/bdns")
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"concesiones_cv_{any_}.jsonl"

    first = _fetch_page(regio, any_, 0)
    total_pages = first.get("totalPages", 1)
    total_elements = first.get("totalElements", len(first.get("content", [])))
    logger.info(
        "BDNS %s regio=%s: %s concessions en %s pagines", any_, regio, total_elements, total_pages
    )

    n = 0
    with out.open("w", encoding="utf-8") as f:
        for rec in first.get("content", []):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
        for page in range(1, total_pages):
            time.sleep(_PAUSA_S)
            data = _fetch_page(regio, any_, page)
            for rec in data.get("content", []):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
            logger.info("  pagina %s/%s (%s registres acumulats)", page + 1, total_pages, n)

    logger.info("Escrites %s concessions a %s", n, out)
    return out


def main() -> None:
    """Baixa uns quants anys recents de concessions de la CV (spike: 2022-2024)."""
    for any_ in (2022, 2023, 2024):
        download_any(any_)


if __name__ == "__main__":
    main()
