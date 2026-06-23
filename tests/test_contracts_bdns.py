"""Proves del contracte BDNS contra una fixture sintetica.

La fixture (tests/fixtures/bdns_raw/concesiones_cv_sample.jsonl) conte NOMES entitats
ficticies, cap dada real (CI corre sempre amb fixtures sinteticas). Reprodueix les
peculiaritats del fitxer real: camp `beneficiario` = "<NIF/CIF> <NOM>", codis ZZ per a
entitats sense NIF estandard, l'artefacte de nom amb `*`, i camps nullable
(descripcionCooficial, nivel3, codigoInvente).

La pregunta critica de l'spike (vegeu docs/sources/bdns.md): el NIF/CIF del beneficiari
persona juridica s'extrau de manera utilitzable? Estos tests ho blinden.
"""

import json
from pathlib import Path

from contracts.bdns import BdnsConcesion

FIXTURE = Path(__file__).parent / "fixtures" / "bdns_raw" / "concesiones_cv_sample.jsonl"


def _load() -> list[BdnsConcesion]:
    with FIXTURE.open(encoding="utf-8") as f:
        return [BdnsConcesion.model_validate(json.loads(line)) for line in f if line.strip()]


def test_la_fixture_valida_sencera():
    rows = _load()
    assert len(rows) == 4


def test_cif_de_persona_juridica_es_extrau():
    coop = _load()[0]
    assert coop.nif_cif == "B00000001"
    assert coop.beneficiary_name == "COOPERATIVA FICTICIA DE PROVA SCV"
    assert coop.is_legal_person is True


def test_artefacte_asterisc_no_trenca_l_extraccio():
    ajunt = _load()[1]
    assert ajunt.nif_cif == "P4600000A"  # ens public: CIF utilitzable
    assert ajunt.is_legal_person is True
    assert ajunt.beneficiary_name.endswith("*")  # l'artefacte queda al nom, no a l'id


def test_codi_zz_no_es_persona_juridica():
    asoc = _load()[2]
    assert asoc.nif_cif == "ZZ009999Z"
    assert asoc.is_legal_person is False  # codi ZZ: no es clau forta de persona juridica


def test_camps_nullable_admeten_none():
    rows = _load()
    assert rows[1].call_title_cooficial is None
    assert rows[1].admin_level3 is None
    assert rows[0].invente_code is None


def test_imports_int_i_float():
    rows = _load()
    assert rows[1].amount_eur == 3000.0  # int a la font -> float
    assert rows[0].amount_eur == 12500.5
