"""Export del mart de juridiques a Parquet, l'artefacte que consulta l'explorador.

Llig el mart de la DuckDB del build plane i l'escriu com a Parquet a data/dist
(gitignored: es un artefacte derivat, no una font). L'explorador el consulta client-side
amb DuckDB-WASM. Sense desplegament: tot local.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from publish.leak_guard import LeakError, assert_mart_parquet_clean

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("publish.export")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ordit.duckdb"
DIST_DIR = ROOT / "data" / "dist"

# Marts a exportar: nom de la taula -> nom del fitxer parquet.
MARTS = {
    "mart_ajudes_pac_juridiques": "mart_ajudes_pac_juridiques.parquet",
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
            # Guard de fuga: cap dada de persona física pot eixir del build plane.
            # Si el Parquet en conté, peta i s'esborra: no es publica res brut.
            try:
                assert_mart_parquet_clean(con, out)
            except LeakError:
                out.unlink(missing_ok=True)
                raise
            n = con.execute(f"select count(*) from {table}").fetchone()[0]
            logger.info("Exportat %s -> %s (%d files, guard de fuga OK)", table, out, n)
            written.append(out)
    finally:
        con.close()
    return written


if __name__ == "__main__":
    export()
