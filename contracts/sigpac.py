"""Contracte de dades de SIGPAC (capa de recintes), validat contra fitxer real 2025.

Font: ICV (Institut Cartografic Valencia), "Recintos SIGPAC de la Comunitat Valenciana",
distribuit per provincia en SHP comprimit (.7z, EPSG:25830). Vegeu docs/sources/sigpac.md
per a procedencia, esquema real i peculiaritats.

Identificadors interns en angles (capa ordit). El renom a columnes valencianes es fa a la
capa marts. Els alies apunten als noms de columna REALS del SHP (confirmats amb ogrinfo
contra el fitxer): MAJUSCULES i TRUNCATS a 10 caracters per la limitacio del format DBF
(p. ex. el camp que el diccionari de l'ICV diu "dn_surface_m2" al SHP es diu "DN_SURFACE").

Decisions de disseny:
- Superficie en Decimal (m2), mai float: es la mesura publicada i s'agrega per municipi.
- USO_SIGPAC i GRUPO_CULT son llistes tancades (vegeu docs/sources/sigpac.md). El contracte
  NO les restringeix amb un Enum: la validacio de valors acceptats viu als tests de dbt
  sobre el mart, no al contracte (la font pot afegir codis i no volem que la ingestio
  peta). group_cult pot ser NULL (usos sense grup de cultiu, p. ex. vials o aigua).
- provincia i municipio son els codis de CATASTRO (DGC), no INE: la resolucio
  catastro -> codi_ine es fa a la capa de models amb un crosswalk (default-deny), no ací.
  Vegeu docs/sources/sigpac.md.
- El recinte porta referencia catastral (poligon/parcel.la/recinte): als marts nomes
  s'agrega a superficie per municipi i us (vegeu marts).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SigpacRecinte(BaseModel):
    """Un recinte SIGPAC: la unitat minima d'us del sol amb superficie i codi cadastral.

    El contracte modela la font tal com es. L'agregacio a superficie per municipi i us
    (l'unic que es publica) es fa a la capa de models, no ací.
    """

    model_config = ConfigDict(populate_by_name=True)

    province_catastro: int = Field(alias="PROVINCIA")  # codi de provincia (catastro = INE)
    municipality_catastro: int = Field(alias="MUNICIPIO")  # codi de municipi de CATASTRO (DGC)
    polygon: int = Field(alias="POLIGONO")  # identificador del poligon cadastral
    parcel: int = Field(alias="PARCELA")  # parcel.la cadastral (mai publicada per recinte)
    recinte: int = Field(alias="RECINTO")  # identificador del recinte SIGPAC
    surface_m2: Decimal = Field(alias="DN_SURFACE")  # superficie del recinte en m2
    land_use: str = Field(alias="USO_SIGPAC")  # codi d'us (llista tancada de 2 lletres)
    crop_group: str | None = Field(default=None, alias="GRUPO_CULT")  # TCR/TCS/CP/PP o NULL

    @field_validator("crop_group", "land_use", mode="before")
    @classmethod
    def _blank_to_none(cls, v: object) -> str | None:
        """Codis de text: buit o NULL -> None (land_use sempre ve, pero ho normalitzem)."""
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @field_validator("surface_m2", mode="before")
    @classmethod
    def _decimal(cls, v: object) -> Decimal:
        """Superficie en m2; el SHP la porta com a real amb punt decimal."""
        if isinstance(v, Decimal):
            return v
        s = str(v).strip() if v is not None else ""
        return Decimal(s) if s else Decimal("0")

    @property
    def catastro_code(self) -> str:
        """Codi de municipi de catastro normalitzat: provincia(2) + municipi(3), zero-pad.

        P. ex. provincia=3, municipi=1 -> "03001". Es la clau de unio amb el crosswalk
        catastro -> codi_ine (vegeu la capa de models).
        """
        return f"{self.province_catastro:02d}{self.municipality_catastro:03d}"
