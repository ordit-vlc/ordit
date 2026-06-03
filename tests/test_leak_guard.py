"""Guard de fuga: cap artefacte committejat o servit conté dades de persona física.

Escaneja els artefactes committejats (seeds, geometria de l'explorador) i prova el gate
del Parquet del mart amb dades sintètiques (cap dada real). Vegeu publish/leak_guard.py i
DATA-PROTECTION.md §6-§7.
"""

from pathlib import Path

import duckdb
import pytest

from publish.leak_guard import (
    LeakError,
    assert_mart_parquet_clean,
    scan_text_artifact,
)

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = sorted(
    [*(ROOT / "ordit_dbt" / "seeds").glob("*.csv"), *(ROOT / "explorer" / "geo").glob("*.geojson")]
)


@pytest.mark.parametrize("path", COMMITTED, ids=lambda p: p.name)
def test_artefactes_committejats_sense_fisiques(path: Path):
    assert scan_text_artifact(path) == [], f"marcador de persona física a {path}"


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    c.execute(
        """
        create table int_fega_classified as
        select * from (values
            ('COOP EXEMPLE COOP V', 'legal'),
            ('ES#00000001', 'natural_masked'),
            ('NOM FICTICI DE PROVA', 'natural')
        ) as t(beneficiary_name, entity_type)
        """
    )
    return c


def _write_mart(con: duckdb.DuckDBPyConnection, tmp_path: Path, names: list[str]) -> Path:
    values = ", ".join(f"('{n}')" for n in names)
    out = tmp_path / "mart.parquet"
    con.execute(
        f"copy (select * from (values {values}) as t(nom_beneficiari)) "
        f"to '{out.as_posix()}' (format parquet)"
    )
    return out


def test_parquet_net_passa(con, tmp_path: Path):
    out = _write_mart(con, tmp_path, ["COOP EXEMPLE COOP V"])
    assert_mart_parquet_clean(con, out)  # no ha de petar


def test_parquet_amb_codi_es_peta(con, tmp_path: Path):
    out = _write_mart(con, tmp_path, ["COOP EXEMPLE COOP V", "ES#00000001"])
    with pytest.raises(LeakError):
        assert_mart_parquet_clean(con, out)


def test_parquet_amb_no_legal_peta(con, tmp_path: Path):
    out = _write_mart(con, tmp_path, ["NOM FICTICI DE PROVA"])
    with pytest.raises(LeakError):
        assert_mart_parquet_clean(con, out)
