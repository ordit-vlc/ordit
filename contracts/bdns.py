"""Contracte de dades de la BDNS (Base de Datos Nacional de Subvenciones).

Font: API JSON publica del SNPSAP/BDNS, endpoint /concesiones/busqueda. Una concessio de
subvencio a nivell d'entitat. A diferencia de FEGA, porta el NIF/CIF del beneficiari
INCRUSTAT al camp `beneficiario` ("<NIF/CIF> <NOM>"), el premi que fa la BDNS l'eix natural
de l'eix "capital de fora". Vegeu docs/sources/bdns.md.

Mode privat (CLAUDE.md §8): es valida i s'ingereix la dada sencera. El BDNS publica les
persones fisiques amb el seu NIF (DNI o NIE), no sota lletra de CIF; els casos de proteccio
especial no es registren (RD 130/2019). Al tall CV 2023 en son ~0 (vegeu docs/sources/bdns.md):
NO venen emmascarades dins dels CIF. L'`*` que apareix en alguns registres es un artefacte del
NOM, no una anonimitzacio de l'identificador.

Identificadors interns en angles (capa ordit); els alies apunten als noms de camp de la font
(camelCase castella, documentats tal qual: es procedencia). El renom a valencia es fa a marts.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, computed_field

# NIF/CIF espanyol: 9 alfanumerics al principi del camp `beneficiario`, separat del nom per
# un espai. Lletra inicial A-W (excepte I/K/L/M/O/T) -> persona juridica (CIF) o ens public;
# DNI de persona fisica -> 8 digits + lletra (comença per digit); NIE -> X/Y/Z + digits +
# lletra. Al tall CV 2023 tots els identificadors comencen per lletra de CIF (cap digit
# inicial, cap `*`): no hi ha fisiques emmascarades. La regex extrau el token de 9 caracters;
# si mai en vinguera un d'emmascarat amb `*`, no casaria (nif_cif=None), que es el desitjat.
_NIF_CIF = re.compile(r"^([0-9A-Z]{9})\s+(.+)$")
_CIF_LETTERS = set("ABCDEFGHJNPQRSUVW")  # persona juridica / ens public


class BdnsConcesion(BaseModel):
    """Una concessio de subvencio de la BDNS (endpoint /concesiones/busqueda)."""

    grant_id: int = Field(alias="id")
    grant_code: str = Field(alias="codConcesion")
    grant_date: str = Field(alias="fechaConcesion")  # YYYY-MM-DD a la font
    beneficiary_raw: str = Field(alias="beneficiario")  # "<NIF/CIF> <NOM>" o emmascarat amb *
    instrument: str = Field(alias="instrumento")
    amount_eur: float = Field(alias="importe")
    equivalent_aid_eur: float = Field(alias="ayudaEquivalente")
    url_br: str | None = Field(default=None, alias="urlBR")
    has_project: bool = Field(alias="tieneProyecto")
    call_number: str | None = Field(default=None, alias="numeroConvocatoria")
    call_id: int | None = Field(default=None, alias="idConvocatoria")
    call_title: str | None = Field(default=None, alias="convocatoria")
    call_title_cooficial: str | None = Field(default=None, alias="descripcionCooficial")
    admin_level1: str | None = Field(default=None, alias="nivel1")  # AUTONOMICA/LOCAL/ESTATAL...
    admin_level2: str | None = Field(default=None, alias="nivel2")
    admin_level3: str | None = Field(default=None, alias="nivel3")
    invente_code: str | None = Field(default=None, alias="codigoInvente")
    person_id: int = Field(alias="idPersona")  # id intern de la BDNS per al beneficiari
    register_date: str | None = Field(default=None, alias="fechaAlta")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def nif_cif(self) -> str | None:
        """NIF/CIF incrustat al principi de `beneficiario`; None si emmascarat o absent."""
        m = _NIF_CIF.match(self.beneficiary_raw.strip())
        return m.group(1) if m else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def beneficiary_name(self) -> str:
        """Nom del beneficiari sense el NIF/CIF inicial (o el cru si no s'ha pogut separar)."""
        m = _NIF_CIF.match(self.beneficiary_raw.strip())
        return m.group(2) if m else self.beneficiary_raw.strip()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_legal_person(self) -> bool:
        """True si el NIF/CIF es de persona juridica o ens public (clau forta utilitzable)."""
        cif = self.nif_cif
        return bool(cif) and cif[0] in _CIF_LETTERS
