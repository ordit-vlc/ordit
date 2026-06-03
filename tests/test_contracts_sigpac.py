"""Proves del contracte SIGPAC contra una fixture sintetica.

La fixture (tests/fixtures/sigpac_sample.csv) reprodueix l'esquema real del SHP de recintes
de l'ICV: noms de columna en MAJUSCULES i TRUNCATS a 10 caracters (DN_SURFACE, GRUPO_CULT...),
provincia/municipi com a enters de catastro, us SIGPAC de dues lletres i grup de cultiu
opcional. No conte cap dada personal (els recintes no en porten).
"""

import csv
from decimal import Decimal
from pathlib import Path

from contracts.sigpac import SigpacRecinte

FIXTURE = Path(__file__).parent / "fixtures" / "sigpac_sample.csv"


def _load() -> list[SigpacRecinte]:
    with FIXTURE.open(encoding="utf-8", newline="") as f:
        return [SigpacRecinte.model_validate(row) for row in csv.DictReader(f)]


def test_la_fixture_valida_sencera():
    rows = _load()
    assert len(rows) == 5


def test_codi_catastro_es_zero_pad_provincia_municipi():
    # provincia=46, municipi=237 -> "46237"; provincia=3, municipi=1 -> "03001".
    rows = _load()
    assert rows[0].catastro_code == "46237"
    assert rows[2].catastro_code == "03001"


def test_superficie_es_decimal():
    primer = _load()[0]
    assert isinstance(primer.surface_m2, Decimal)
    assert primer.surface_m2 == Decimal("15234.55")


def test_grup_de_cultiu_buit_es_none():
    # La tercera fila (FL) i la d'edificacions no porten grup de cultiu.
    rows = _load()
    assert rows[2].crop_group is None
    assert rows[4].crop_group is None
    assert rows[0].crop_group == "TCR"


def test_us_sempre_present():
    assert all(r.land_use for r in _load())
