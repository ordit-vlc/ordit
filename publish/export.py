"""Export dels marts a Parquet, l'artefacte que consulta l'explorador.

Llig els marts de la DuckDB del build plane i els escriu com a Parquet a data/dist
(gitignored: es un artefacte derivat, no una font). L'explorador el consulta client-side
amb DuckDB-WASM. Sense desplegament: tot local.

Mode privat (vegeu CLAUDE.md): res no es publica fora del build plane local; per aixo
l'export no aplica cap filtre ni guard d'anonimitzacio. Eixe pas es fara a una fase
dedicada del ROADMAP abans de qualsevol publicacio.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("publish.export")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ordit.duckdb"
DIST_DIR = ROOT / "data" / "dist"

# Marts a exportar: nom de la taula -> nom del fitxer parquet. L'explorador consulta cada
# Parquet client-side amb DuckDB-WASM. Tres capes: ajudes de la PAC (tots els receptors),
# superficie de cultiu de SIGPAC per municipi i us, i el creuat diners-PAC x superficie.
MARTS = {
    "mart_ajudes_pac": "mart_ajudes_pac.parquet",
    "mart_superficie_cultiu_municipi": "mart_superficie_cultiu_municipi.parquet",
    "mart_pac_x_superficie_municipi": "mart_pac_x_superficie_municipi.parquet",
}


def export(db_path: Path = DB_PATH, dist_dir: Path = DIST_DIR) -> list[Path]:
    """Exporta els marts a Parquet. Torna les rutes escrites."""
    if not db_path.exists():
        raise FileNotFoundError(
            f"no s'ha trobat {db_path}; executa `just build` (dbt build) abans de publicar."
        )
    dist_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        for table, filename in MARTS.items():
            out = dist_dir / filename
            con.execute(f"copy (select * from {table}) to '{out.as_posix()}' (format parquet)")
            n = con.execute(f"select count(*) from {table}").fetchone()[0]
            logger.info("Exportat %s -> %s (%d files)", table, out, n)
            written.append(out)
    finally:
        con.close()
    return written


if __name__ == "__main__":
    export()
