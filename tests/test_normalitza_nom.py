"""Normalitzacio de noms de beneficiari truncats en origen (crosswalk xwalk_beneficiari).

Sintetic (sempre, CI-safe): construeix els marts contra les fixtures (que inclouen una fila
"VALENCIANA") i comprova que el nom truncat NO sobreviu al mart i que hi apareix el nom
normalitzat "Generalitat Valenciana".

Real (nomes en local, si data/ordit.duckdb existeix): el cas confirmat de FEGA queda
corregit i conserva l'import agregat (~15,1 ME en 7 files).
"""

import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT / "ordit_dbt"
SYNTH_GLOB = str(
    ROOT / "tests" / "fixtures" / "raw" / "Beneficiarios_municipio_ejercicio_financiero_*.utf8.txt"
)
# El mart depen de l'enllac amb cooperatives (staging_cooperatives) -> fixtures CI-safe.
COOP_GLOB = str(ROOT / "tests" / "fixtures" / "cooperatives_raw" / "*.jsonl")
REAL_DB = ROOT / "data" / "ordit.duckdb"


@pytest.fixture(scope="module")
def synth_marts_db(tmp_path_factory) -> Path:
    """Construeix els marts contra les fixtures sintetiques en una DuckDB temporal."""
    db_path = tmp_path_factory.mktemp("dbt") / "test.duckdb"
    env = {**os.environ, "DUCKDB_PATH": str(db_path)}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dbt.cli.main",
            "build",
            "--select",
            "+mart_ajudes_pac",
            # Nomes els tests amb TOTS els refs seleccionats: evita arrossegar tests de
            # relacio de seeds no relacionats (p. ex. xwalk_catastro_ine) que no es construeixen.
            "--indirect-selection",
            "cautious",
            "--profiles-dir",
            ".",
            "--vars",
            f"{{fega_raw_glob: '{SYNTH_GLOB}', cooperatives_raw_glob: '{COOP_GLOB}'}}",
        ],
        cwd=DBT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"dbt build ha fallat:\n{result.stdout}\n{result.stderr}"
    return db_path


def test_nom_truncat_no_sobreviu(synth_marts_db: Path):
    con = duckdb.connect(str(synth_marts_db), read_only=True)
    n_truncat = con.execute(
        "select count(*) from mart_ajudes_pac where nom_beneficiari = 'VALENCIANA'"
    ).fetchone()[0]
    assert n_truncat == 0, "el nom truncat 'VALENCIANA' no s'ha normalitzat"


def test_nom_normalitzat_present(synth_marts_db: Path):
    con = duckdb.connect(str(synth_marts_db), read_only=True)
    n_norm = con.execute(
        "select count(*) from mart_ajudes_pac where nom_beneficiari = 'Generalitat Valenciana'"
    ).fetchone()[0]
    assert n_norm >= 1, "no apareix el nom normalitzat 'Generalitat Valenciana'"


@pytest.mark.skipif(not REAL_DB.exists(), reason="sense data/ordit.duckdb (no construit en local)")
def test_cas_real_conserva_import():
    """El cas real de FEGA queda corregit i conserva l'import agregat (~15,1 ME, 7 files)."""
    con = duckdb.connect(str(REAL_DB), read_only=True)
    assert (
        con.execute(
            "select count(*) from mart_ajudes_pac where nom_beneficiari = 'VALENCIANA'"
        ).fetchone()[0]
        == 0
    )
    imp, n = con.execute(
        "select sum(import_eur), count(*) from mart_ajudes_pac "
        "where nom_beneficiari = 'Generalitat Valenciana'"
    ).fetchone()
    assert 15_000_000 <= float(imp) <= 15_200_000, imp
    assert n == 7, n
