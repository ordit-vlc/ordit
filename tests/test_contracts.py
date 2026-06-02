"""Proves del contracte FEGA contra una fixture sintetica.

La fixture (tests/fixtures/fega_sample.csv) conte NOMES entitats juridiques ficticies,
cap dada de persona fisica real (vegeu DATA-PROTECTION.md). Reprodueix les peculiaritats
del fitxer real: delimitador ";", coma decimal, OBJETIVO_ESP multivalor amb "|" i dates
DD/MM/YYYY. L'exercici no ve a la font: s'injecta com fa la ingestio des del nom de fitxer.
"""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from contracts.fega import FegaBeneficiary

FIXTURE = Path(__file__).parent / "fixtures" / "fega_sample.csv"
FIXTURE_YEAR = 2024  # com el derivaria la ingestio del nom de fitxer


def _load() -> list[FegaBeneficiary]:
    with FIXTURE.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        return [
            FegaBeneficiary.model_validate({**row, "financial_year": FIXTURE_YEAR})
            for row in reader
        ]


def test_la_fixture_valida_sencera():
    rows = _load()
    assert len(rows) == 4
    assert all(r.financial_year == 2024 for r in rows)


def test_imports_son_decimal_amb_coma():
    coop = _load()[0]
    assert isinstance(coop.amount_total_eur, Decimal)
    assert coop.amount_total_eur == Decimal("1234.56")
    assert coop.amount_feaga == Decimal("1234.56")
    assert coop.amount_feader == Decimal("0")


def test_objectius_multivalor_es_parteixen_per_pipe():
    societat = _load()[1]
    assert societat.specific_objectives == ["OE4", "OE5", "OE6"]
    coop = _load()[0]
    assert coop.specific_objectives == ["OE1"]
    exportadora = _load()[2]
    assert exportadora.specific_objectives == []


def test_dates_dmy_i_camps_opcionals():
    fundacio = _load()[3]
    assert fundacio.date_start == date(2023, 8, 2)
    coop = _load()[0]
    assert coop.date_start is None
    assert coop.group_raw is None


def test_grupo_empresa_es_deixa_cru():
    societat = _load()[1]
    # La particio en group_cif + group_name es fa a staging (Fase 1), no al contracte.
    assert societat.group_raw == "A12345678-GRUP DEMO SA"
