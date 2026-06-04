"""Contracte de dades de BORME (spike de la Fase 3), validat contra una mostra real.

Font: BOE - Datos Abiertos, Boletin Oficial del Registre Mercantil (BORME), Seccio A
(Empresaris. Actes inscrits). Vegeu docs/sources/borme.md per a procedencia, llicencia i
peculiaritats.

Spike d'enllac per NOM: el BORME-A NO porta CIF (nomes el numero de full registral i les
dades del Registre Mercantil). La identitat depen, doncs, del nom -- igual que a FEGA. Per
aixo este spike mesura si l'enllac per nom es viable abans de comprometre splink.

Identificadors interns en angles ASCII (capa ordit); els alies apunten als noms dels camps
del registre parsejat (vegeu ingest/borme/download.py).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class BormeCompany(BaseModel):
    """Una empresa inscrita al BORME-A d'una provincia de la Comunitat Valenciana.

    Una mateixa empresa pot apareixer en diversos actes/dies (el BORME es un flux d'actes,
    no una instantania del registre); la deduplicacio per nom es fa a la capa de mesura.
    """

    company_name: str = Field(alias="nom")  # rao social tal com surt al BORME-A
    registry_number: str | None = Field(default=None, alias="num_registre")  # full registral
    province_code: str = Field(alias="provincia")  # 03 Alacant, 12 Castello, 46 Valencia
    source_id: str = Field(alias="font_id")  # identificador de l'item (BORME-A-AAAA-NN-PP)
    publication_date: date = Field(alias="data")  # data de publicacio del BORME
    # CIF/NIF: no existeix al BORME-A; per aixo l'enllac es nomes per nom.
