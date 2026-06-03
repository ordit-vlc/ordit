"""Sanity de l'export: els tres marts es publiquen com a Parquet amb comptes coherents.

Sintetic (sempre, CI-safe): construeix una DuckDB temporal amb els tres marts (taules
minimes, entitats ficticies) i comprova que `publish.export.export` escriu exactament tres
Parquet i que cada Parquet te tantes files com la taula d'origen (cap perdua silenciosa).

Real (nomes en local, si `data/ordit.duckdb` existeix): comprova els ordres de magnitud
esperats del build real (mart_ajudes_pac ~275k, superficie 10.507, creuat 542). Mai corre
a CI, on no hi ha dades reals.
"""

from pathlib import Path

import duckdb
import pytest

from publish.export import MARTS, export

ROOT = Path(__file__).resolve().parents[1]
REAL_DB = ROOT / "data" / "ordit.duckdb"


@pytest.fixture()
def synthetic_db(tmp_path: Path) -> Path:
    """DuckDB temporal amb els tres marts, cada un amb un compte de files distint."""
    db_path = tmp_path / "synth.duckdb"
    con = duckdb.connect(str(db_path))
    counts = {
        "mart_ajudes_pac": 5,
        "mart_superficie_cultiu_municipi": 3,
        "mart_pac_x_superficie_municipi": 2,
    }
    for table, n in counts.items():
        con.execute(f"create table {table} as select range as i from range({n})")
    con.close()
    return db_path


def test_export_genera_els_tres_parquet(synthetic_db: Path, tmp_path: Path):
    dist = tmp_path / "dist"
    written = export(db_path=synthetic_db, dist_dir=dist)

    # Un Parquet per mart, exactament els tres declarats a MARTS.
    assert {p.name for p in written} == set(MARTS.values())
    assert len(written) == 3

    # Cada Parquet conserva el compte de files de la seua taula (cap perdua).
    con = duckdb.connect()
    for table, filename in MARTS.items():
        out = dist / filename
        assert out.exists(), f"falta {filename}"
        n_parquet = con.execute(f"select count(*) from '{out.as_posix()}'").fetchone()[0]
        n_taula = (
            duckdb.connect(str(synthetic_db), read_only=True)
            .execute(f"select count(*) from {table}")
            .fetchone()[0]
        )
        assert n_parquet == n_taula, f"{filename}: {n_parquet} files != {n_taula} a la taula"
    con.close()


@pytest.mark.skipif(not REAL_DB.exists(), reason="sense data/ordit.duckdb (no construit en local)")
def test_export_real_ordres_de_magnitud(tmp_path: Path):
    """Comprovacio lleugera contra el build real local: comptes en l'ordre esperat."""
    con = duckdb.connect(str(REAL_DB), read_only=True)
    n_ajudes = con.execute("select count(*) from mart_ajudes_pac").fetchone()[0]
    n_sup_us = con.execute("select count(*) from mart_superficie_cultiu_municipi").fetchone()[0]
    n_creuat = con.execute("select count(*) from mart_pac_x_superficie_municipi").fetchone()[0]
    con.close()
    assert 250_000 <= n_ajudes <= 300_000, n_ajudes
    assert n_sup_us == 10_507, n_sup_us
    assert n_creuat == 542, n_creuat
