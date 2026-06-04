"""Ingesta de SAT (Fase 3): parseig pur i contracte, amb fixtures sintetiques (CI-safe)."""

from pathlib import Path

from contracts.sat import Sat
from ingest.sat.download import parse_csv

FIXTURE = Path(__file__).parent / "fixtures" / "sat" / "sat_sample.csv"


def test_parse_csv_i_contracte():
    records = parse_csv(FIXTURE.read_text(encoding="utf-8"))
    assert len(records) == 2
    sats = [Sat(**r) for r in records]
    assert sats[0].registry_number == "9999"
    assert sats[0].company_name == "EXEMPLE FICTICI"
    assert sats[0].municipality == "EXEMPLE DE DALT"
    assert sats[0].status == "ALTA"
    # NO porta CIF (com BORME): cap camp de CIF al contracte.
    assert "cif" not in Sat.model_fields and "nif" not in Sat.model_fields


def test_parse_csv_salta_files_sense_denominacio():
    records = parse_csv(FIXTURE.read_text(encoding="utf-8") + "\n;;;;;;;\n")
    assert len(records) == 2
