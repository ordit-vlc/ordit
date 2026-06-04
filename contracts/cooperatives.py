"""Contracte de dades del Directori de Cooperatives de la Comunitat Valenciana.

Font: GVA, dadesobertes.gva.es, "Directorio de Cooperativas de la Comunitat Valenciana"
(CC-BY, CSV anual). Vegeu docs/sources/cooperatives.md.

A diferencia de FEGA i BORME-A, ESTA font SI porta CIF (CD_NIF): es el premi de l'enllac
(injecta a FEGA el CIF que no te). Identificadors interns en angles ASCII; els alies apunten
als noms REALS de columna de la font (majuscules, castella).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Cooperative(BaseModel):
    """Una cooperativa inscrita al Registre de Cooperatives de la Comunitat Valenciana."""

    cif: str = Field(alias="CD_NIF")  # NIF/CIF de la cooperativa (el premi de l'enllac)
    company_name: str = Field(alias="DS_RAZON_SOCIAL")  # rao social
    registry_key: str | None = Field(default=None, alias="CD_CLAVE_REGISTRAL")  # clau registral
    address: str | None = Field(default=None, alias="DS_DOMICILIO")
    province_code: str | None = Field(default=None, alias="CD_PROVINCIA")  # 03/12/46
    province_name: str | None = Field(default=None, alias="DS_PROVINCIA")
    municipality_code: str | None = Field(default=None, alias="CD_MUNICIPIO")
    municipality: str | None = Field(default=None, alias="DS_MUNICIPIO")  # nom del municipi
    coop_class: str | None = Field(default=None, alias="DS_CLASE")  # p. ex. TRABAJO ASOCIADO
