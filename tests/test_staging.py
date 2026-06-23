"""Guard #1: les columnes de staging_fega no poden derivar del contracte FegaBeneficiary.

Construeix el model staging_fega contra fixtures sintetiques (NOMES entitats ficticies,
cap dada de persona fisica) i afirma que el conjunt de columnes coincideix exactament amb
els camps del contracte contracts/fega.py. Si la font (o el model) afig o lleva una
columna, este test trenca: cap deriva silenciosa.

Tambe verifica que el filtre a la Comunitat Valenciana s'aplica (les files de fora de la
CV no entren a staging).
"""

import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from contracts.fega import FegaBeneficiary

ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT / "ordit_dbt"
SYNTH_GLOB = str(
    ROOT / "tests" / "fixtures" / "raw" / "Beneficiarios_municipio_ejercicio_financiero_*.utf8.txt"
)


@pytest.fixture(scope="module")
def staging_db(tmp_path_factory) -> Path:
    """Construeix staging_fega contra les fixtures sintetiques en una DuckDB temporal."""
    db_path = tmp_path_factory.mktemp("dbt") / "test.duckdb"
    env = {**os.environ, "DUCKDB_PATH": str(db_path)}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            "build",
            "--select",
            "staging_fega",
            # Nomes el model, sense tests indirectes: este guard inspecciona columnes de
            # staging, no els marts. Sense aixo, dbt (indirect-selection eager) arrossegaria
            # tests singulars que referencien staging_fega pero tambe marts no construits ací.
            "--indirect-selection",
            "empty",
            "--profiles-dir",
            ".",
            "--vars",
            f"{{fega_raw_glob: '{SYNTH_GLOB}'}}",
        ],
        cwd=DBT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"dbt build ha fallat:\n{result.stdout}\n{result.stderr}"
    return db_path


# Columnes derivades que staging afig a banda del contracte (split de MUNICIPIO).
_DERIVED = {"postal_code", "locality_raw"}


def test_columnes_staging_igualen_el_contracte(staging_db: Path):
    con = duckdb.connect(str(staging_db), read_only=True)
    cols = {row[0] for row in con.execute("describe staging_fega").fetchall()}
    expected = set(FegaBeneficiary.model_fields)
    # Tots els camps del contracte hi son (cap deriva silenciosa de la font)...
    assert expected <= cols, f"falten camps del contracte: {expected - cols}"
    # ...i les uniques columnes extra son les derivades esperades.
    assert cols - expected <= _DERIVED, f"columnes inesperades: {cols - expected - _DERIVED}"


def test_filtre_comunitat_valenciana(staging_db: Path):
    con = duckdb.connect(str(staging_db), read_only=True)
    rows = con.execute("select distinct province from staging_fega").fetchall()
    provinces = {row[0] for row in rows}
    # La fixture inclou una fila de Madrid que NO ha d'entrar.
    assert "Madrid" not in provinces
    assert provinces <= {"València/Valencia", "Castelló/Castellón", "Alacant/Alicante"}
