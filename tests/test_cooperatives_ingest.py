"""Ingesta de cooperatives (Fase 3): reparacio d'encoding, parseig i contracte.

Sense xarxa (CI-safe): la fixture porta el mateix doble-mojibake que la font real; el parser
i la reparacio son funcions pures i la sortida valida contra el contracte Cooperative.
"""

from pathlib import Path

from contracts.cooperatives import Cooperative
from ingest.cooperatives.download import parse_csv, repair_mojibake

FIXTURE = Path(__file__).parent / "fixtures" / "cooperatives" / "cooperativas_sample.csv"


def _text() -> str:
    return repair_mojibake(FIXTURE.read_bytes().decode("utf-8", "replace"))


def test_repair_mojibake_recupera_accents():
    text = _text()
    assert "VALÈNCIA" in text  # doble-mojibake reparat
    assert "Nº" in text
    assert "Ã" not in text and "Â" not in text  # cap residu


def test_parse_csv_i_contracte():
    records = parse_csv(_text())
    assert len(records) == 2
    coops = [Cooperative(**r) for r in records]
    assert coops[0].cif == "F00000001"
    assert coops[0].company_name == "COOPERATIVA EXEMPLE COOP. V."
    assert coops[0].registry_key == "V-0001"
    assert coops[0].municipality == "EXEMPLE DE DALT"
    assert coops[0].province_code == "46"
    # ESTA font SI porta CIF (a diferencia de FEGA i BORME).
    assert "cif" in Cooperative.model_fields


def test_parse_csv_salta_files_buides():
    records = parse_csv(_text() + "\n;;;;;;;;\n")
    assert len(records) == 2  # la fila sense rao social no entra
