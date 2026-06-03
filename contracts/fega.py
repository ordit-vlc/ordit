"""Contracte de dades de FEGA, validat contra un fitxer real de l'exercici 2024.

Font: FEGA dades obertes, "Datos transparencia beneficiarios por municipio" (fitxer
nacional per municipi i exercici). Vegeu docs/sources/fega.md per a procedencia, esquema
real i peculiaritats.

Identificadors interns en angles (capa ordit). El renom a columnes valencianes es fa a la
capa marts. Els alies apunten als noms de columna REALS de la font (confirmats contra el
fitxer): majuscules, castella.

Decisions de disseny (PAS B):
- Imports en Decimal, mai float (diners publics). La font usa coma decimal (format
  espanyol); es normalitza ací.
- No hi ha comarca_agraria al fitxer per municipi: els municipis sensibles s'emmascaren
  com "PPXXX - XXXXX". El camp no existeix al contracte.
- financial_year NO ve en cap columna: viu al nom del fitxer i l'injecta la ingestio
  (Fase 1). Ací es un camp requerit sense alias de font.
- FEAGA i FEADER son columnes d'import separades; no hi ha una columna "fondo".
- GRUPO_EMPRESA es deixa CRU ("CIF-NOM"); la particio en group_cif + group_name es fa a
  staging (Fase 1), no al contracte.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_AMOUNT_FIELDS = (
    "amount_feaga",
    "amount_feader",
    "amount_cofin",
    "amount_feader_cofin",
    "amount_total_eur",
)


class FegaBeneficiary(BaseModel):
    """Una linia de transparencia de FEGA (una mesura d'un beneficiari).

    Mode privat (vegeu CLAUDE.md §8): el contracte modela la font tal com es, amb tots els
    receptors (fisiques i juridiques). Cap filtre per tipus d'entitat.
    """

    model_config = ConfigDict(populate_by_name=True)

    beneficiary_name: str = Field(alias="BENEFICIARIO")  # rao social, nom, o codi ES#... anonim
    group_raw: str | None = Field(default=None, alias="GRUPO_EMPRESA")  # "CIF-NOM" cru del grup
    province: str = Field(alias="PROVINCIA")  # etiqueta bilingue a la CV
    # "CODI - Nom"; emmascarat com "PPXXX - XXXXX" si el municipi es xicoteta
    municipality: str | None = Field(default=None, alias="MUNICIPIO")
    measure: str = Field(alias="MEDIDA")  # codi + descripcio en un sol camp
    # OBJETIVO_ESP es multivalor separat per "|"
    specific_objectives: list[str] = Field(default_factory=list, alias="OBJETIVO_ESP")
    date_start: date | None = Field(default=None, alias="FEC_INI")  # operacions plurianuals
    date_end: date | None = Field(default=None, alias="FEC_FIN")
    amount_feaga: Decimal = Field(alias="FEAGA")
    amount_feader: Decimal = Field(alias="FEADER")
    amount_cofin: Decimal = Field(alias="IMPORTECOFIN")
    amount_feader_cofin: Decimal = Field(alias="FEADER_COFIN")
    amount_total_eur: Decimal = Field(alias="IMPORTE_EUROS")
    financial_year: int  # injectat per la ingestio des del nom de fitxer, no ve de la font

    @field_validator("group_raw", "municipality", mode="before")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        """Camps de text opcionals: buit -> None."""
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("specific_objectives", mode="before")
    @classmethod
    def _split_objectives(cls, v: object) -> list[str]:
        """OBJETIVO_ESP es multivalor separat per "|" (p. ex. "OE4|OE5|OE6")."""
        if isinstance(v, list):
            return v
        if not v or not str(v).strip():
            return []
        return [part.strip() for part in str(v).split("|") if part.strip()]

    @field_validator("date_start", "date_end", mode="before")
    @classmethod
    def _parse_dmy(cls, v: object) -> date | None:
        """Dates en format DD/MM/YYYY; buit -> None."""
        if v is None or isinstance(v, date):
            return v
        s = str(v).strip()
        if not s:
            return None
        return datetime.strptime(s, "%d/%m/%Y").date()

    @field_validator(*_AMOUNT_FIELDS, mode="before")
    @classmethod
    def _decimal_es(cls, v: object) -> Decimal:
        """Imports en format espanyol: punt de milers (si n'hi ha) i coma decimal."""
        if isinstance(v, Decimal):
            return v
        s = str(v).strip() if v is not None else ""
        if not s:
            return Decimal("0")
        return Decimal(s.replace(".", "").replace(",", "."))
