"""Proves del contracte FEGA.

A la Fase 0 nomes validem la logica del contracte (alies, tipus, opcionals) sense cap
fitxer de mostra real ni cap crida de xarxa. La validacio contra fitxers reals de FEGA
arriba a la Fase 1, quan es committegen mostres xicotetes a tests/fixtures/.
"""

from contracts.fega import FegaBeneficiary


def test_construeix_des_dels_alies_de_la_font():
    """El contracte accepta els noms de columna de la font (castella, provisionals)."""
    registre = {
        "nombre_beneficiario": "COOPERATIVA AGRICOLA EXEMPLE COOP. V.",
        "nif": "F46000000",
        "municipio": "Carcaixent",
        "comarca_agraria": "La Ribera Alta",
        "provincia": "Valencia",
        "codigo_operacion": "II.1",
        "objetivo_especifico": None,
        "importe_eur": 12345.67,
        "fondo": "FEAGA",
        "ejercicio": 2023,
    }

    b = FegaBeneficiary.model_validate(registre)

    assert b.beneficiary_name == "COOPERATIVA AGRICOLA EXEMPLE COOP. V."
    assert b.nif == "F46000000"
    assert b.amount_eur == 12345.67
    assert b.fund == "FEAGA"
    assert b.financial_year == 2023


def test_municipi_i_nif_son_opcionals():
    """Municipi None (agregat a comarca) i NIF None (registre anonim) son valids."""
    registre = {
        "nombre_beneficiario": "Beneficiari anonim < 1.250 EUR",
        "provincia": "Castello",
        "codigo_operacion": "I.3",
        "importe_eur": 800.0,
        "fondo": "FEADER",
        "ejercicio": 2022,
    }

    b = FegaBeneficiary.model_validate(registre)

    assert b.municipality is None
    assert b.nif is None
    assert b.comarca_agraria is None
