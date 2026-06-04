"""Ingesta de BORME (spike Fase 3): parseig pur i contracte, amb fixtures sintetiques.

Sense xarxa (CI-safe): el parser opera sobre un XML de BORME-A ficticii i la sortida valida
contra el contracte pydantic BormeCompany.
"""

from datetime import date
from pathlib import Path

from contracts.borme import BormeCompany
from ingest.borme.download import cv_items, parse_borme_a

FIXTURE = Path(__file__).parent / "fixtures" / "borme" / "BORME-A-2024-99-46.xml"


def test_parse_borme_a_extrau_empreses():
    records = parse_borme_a(FIXTURE.read_bytes(), "BORME-A-2024-99-46", "46", "2024-02-15")
    noms = [r["nom"] for r in records]
    # Tres empreses; el paragraf d'acte sense "{num} - NOM." no ha d'entrar.
    assert noms == [
        "HORT EXEMPLE SOCIEDAD LIMITADA",
        "COOPERATIVA FICTICIA COOP. V",
        "MAS FICTICI SL",
    ]
    assert records[0]["num_registre"] == "900001"
    assert records[0]["provincia"] == "46"
    assert records[0]["font_id"] == "BORME-A-2024-99-46"


def test_records_validen_el_contracte():
    records = parse_borme_a(FIXTURE.read_bytes(), "BORME-A-2024-99-46", "46", "2024-02-15")
    models = [BormeCompany(**r) for r in records]
    assert models[0].company_name == "HORT EXEMPLE SOCIEDAD LIMITADA"
    assert models[0].province_code == "46"
    assert models[0].publication_date == date(2024, 2, 15)
    # BORME-A no porta CIF: cap camp de CIF al contracte.
    assert "cif" not in BormeCompany.model_fields
    assert "nif" not in BormeCompany.model_fields


def test_cv_items_filtra_provincies_cv():
    sumari = {
        "data": {
            "sumario": {
                "diario": [
                    {
                        "sumario_diario": {
                            "seccion": [
                                {
                                    "codigo": "A",
                                    "item": [
                                        {
                                            "identificador": "BORME-A-2024-99-46",
                                            "url_xml": {"texto": "https://x/46"},
                                        },
                                        {
                                            # Madrid (28), fora de la CV: no ha d'eixir.
                                            "identificador": "BORME-A-2024-99-28",
                                            "url_xml": {"texto": "https://x/28"},
                                        },
                                    ],
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }
    items = cv_items(sumari)
    assert [(i[0], i[1]) for i in items] == [("BORME-A-2024-99-46", "46")]
