"""Reconciliacio de comptes a staging (footgun d'ignore_errors).

Sintetic (sempre): cap fila es perd en el parseig de les fixtures.
Real (nomes en local, si els fitxers existeixen): el forat entre linies del raw i files
parsejades no pot superar la tolerancia; si creix, la font ha derivat i cal revisar-ho.
"""

from pathlib import Path

import pytest

from ingest.fega.reconcile import reconcile

ROOT = Path(__file__).resolve().parents[1]
SYNTH_DIR = ROOT / "tests" / "fixtures" / "raw"
REAL_DIR = ROOT / "data" / "raw" / "fega"

# Baseline observat: 0 files perdudes (DuckDB absorbeix fins i tot les ~2 malformades).
# Tolerem un forat xicotet per a no trencar per soroll, pero alertem si creix de veres.
MAX_DROPPED = 10

_SYNTH = sorted(SYNTH_DIR.glob("*.utf8.txt"))
_REAL = sorted(REAL_DIR.glob("*.utf8.txt"))


@pytest.mark.parametrize("path", _SYNTH, ids=lambda p: p.name)
def test_reconciliacio_sintetica(path: Path):
    r = reconcile(path)
    assert r["dropped"] == 0, r
    assert r["parsed"] == r["raw_data_lines"]


@pytest.mark.skipif(not _REAL, reason="sense fitxers reals (no s'ha ingerit en local)")
@pytest.mark.parametrize("path", _REAL, ids=lambda p: p.name)
def test_reconciliacio_real(path: Path):
    r = reconcile(path)
    assert r["dropped"] <= MAX_DROPPED, (
        f"el forat ha crescut a {r['dropped']} files a {path.name}: la font pot haver "
        f"derivat; revisa el parseig (reconciliacio: {r})"
    )
