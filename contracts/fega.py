from pydantic import BaseModel, Field


class FegaBeneficiary(BaseModel):
    """Un registre de transparencia de FEGA. Publicacio oberta: nomes persones juridiques.

    Font: FEGA dades obertes, fitxers de beneficiaris per municipi i exercici. Els
    municipis xicotets s'agreguen a comarca agraria; les persones fisiques per davall de
    1.250 EUR s'anonimitzen en origen.

    Identificadors interns en angles (capa ordit). El renom a columnes valencianes es fa
    a la capa marts. Els alies apunten als noms de columna de la font (provisionals).
    """

    beneficiary_name: str = Field(alias="nombre_beneficiario")  # rao social o etiqueta anonima
    nif: str | None = Field(default=None, alias="nif")  # CIF de persona juridica; None si anonim
    municipality: str | None = Field(default=None, alias="municipio")  # None si s'agrega a comarca
    comarca_agraria: str | None = Field(default=None, alias="comarca_agraria")
    province: str = Field(alias="provincia")
    operation_code: str = Field(alias="codigo_operacion")  # codi de mesura/sector/intervencio
    specific_objective: str | None = Field(default=None, alias="objetivo_especifico")
    amount_eur: float = Field(alias="importe_eur")
    fund: str = Field(alias="fondo")  # "FEAGA" o "FEADER"
    financial_year: int = Field(alias="ejercicio")  # any financer (16 oct n-1 a 15 oct n)
