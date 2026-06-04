"""Contracte de dades del Registre de SAT (Societats Agraries de Transformacio) de la CV.

Font: GVA, dadesobertes.gva.es, "Sociedades Agrarias de Transformación cuyo ámbito sea la
Comunitat Valenciana" (CC-BY, CSV). Vegeu docs/sources/sat.md.

NO porta CIF (com BORME-A); l'identificador registral es el numero de registre. Els alies
apunten als noms REALS de columna de la font (majuscules, castella, amb accents).
Identificadors interns en angles ASCII.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Sat(BaseModel):
    """Una Societat Agraria de Transformacio inscrita al registre d'ambit valencia."""

    registry_number: str = Field(alias="Nº REGISTRO")  # identificador registral (no CIF)
    company_name: str = Field(alias="DENOMINACIÓN")  # denominacio
    status: str | None = Field(default=None, alias="SITUACIÓN")  # ALTA / BAJA ...
    address: str | None = Field(default=None, alias="DOMICILIO SOCIAL")
    municipality: str | None = Field(default=None, alias="MUNICIPIO")  # desambiguador de l'enllac
    province_name: str | None = Field(default=None, alias="PROVÍNCIA")
    postal_code: str | None = Field(default=None, alias="C.P.")
    num_members: str | None = Field(default=None, alias="Nº SOCIOS")
    # CIF/NIF: no existeix a esta font; l'enllac amb FEGA es per nom + municipi (+ numero
    # de registre extret del nom de FEGA), i s'arrossega numero_registre.
