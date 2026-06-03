# Fil: SIGPAC — recintes amb ús del sòl (Comunitat Valenciana)

Capa gràfica de recintes del Sistema d'Informació Geogràfica de Parcel·les Agrícoles
(SIGPAC), que aporta la superfície i l'ús del sòl assignat a cada recinte. És la base de la
Fase 2: superfície de cultiu per municipi, unida als diners de la PAC de FEGA.

## Procedència i llicència

| Material | Font | Llicència |
|----------|------|-----------|
| Recintes SIGPAC (geometria + atributs) | **ICV — Institut Cartogràfic Valencià**, via [GVA Dades Obertes](https://dadesobertes.gva.es/dataset/sistema-de-informacion-geografica-de-parcelas-agricolas-de-la-comunitat-valenciana-sigpac-2025) i IDEV | **CC BY** (atribució a l'ICV / GVA) |
| Crosswalk codi de municipi de catastro ↔ codi INE | **FEGA**, [«Relación de municipios con equivalencias entre los códigos INE y Catastro» (campanya 2026)](https://www.fega.gob.es/es/content/relacion-de-municipios-por-ccaa-con-equivalencias-entre-los-codigos-ine-y-catastro-2026) | Reutilització de FEGA (atribució) |
| Diccionari de camps de la capa de recintes | [ICV — definició de dades SIGPAC](https://icvficherosweb.icv.gva.es/04/geonetwork/definicion_datos/1403_pac_mdatos.pdf) | CC BY |

- **Cadència**: anual. Campanya ingerida: **2025** (dades a 10-01-2025).
- **Distribució**: SHP comprimit (`.7z`), un fitxer per província, EPSG:25830. La descàrrega
  per recorte (GPKG) i els serveis WMS/WFS també existeixen però no s'usen.
- **Data de descàrrega**: 2026-06-03 (confirmat amb HEAD).

URL de descàrrega (recintes, campanya 2025):

```
https://descargas.icv.gva.es/dcd/14_mediorural/03_pac/2025_SIGPAC_0050/1403_2025PALI_SIGPAC_RECINTOS_25830_SHP.7z  (Alacant, 322 MB)
https://descargas.icv.gva.es/dcd/14_mediorural/03_pac/2025_SIGPAC_0050/1403_2025PCAS_SIGPAC_RECINTOS_25830_SHP.7z  (Castelló, 350 MB)
https://descargas.icv.gva.es/dcd/14_mediorural/03_pac/2025_SIGPAC_0050/1403_2025PVAL_SIGPAC_RECINTOS_25830_SHP.7z  (València, 618 MB)
```

## Esquema real (capa RECINTO del SHP)

Confirmat amb `ogrinfo` contra el fitxer real (el definidor go/no-go de la Fase 2). **Els
noms de columna del SHP venen en MAJÚSCULES i TRUNCATS a 10 caràcters** per la limitació del
format DBF: el camp que el diccionari de l'ICV anomena `dn_surface_m2` al SHP és `DN_SURFACE`.

Camps que usem (vegeu `contracts/sigpac.py`):

| Columna SHP | Significat | Ús |
|-------------|-----------|-----|
| `DN_SURFACE` | Superfície del recinte (m²) | la mètrica que s'agrega |
| `USO_SIGPAC` | Codi d'ús del sòl (llista tancada, 2 lletres) | dimensió principal |
| `GRUPO_CULT` | Grup de cultiu (TCR/TCS/CP/PP…) | facet de cultiu |
| `PROVINCIA`, `MUNICIPIO` | Codi de municipi de **CATASTRO (DGC)**, no INE | clau de unió (via crosswalk) |
| `POLIGONO`, `PARCELA`, `RECINTO` | Referència cadastral del recinte | **mai publicada** (s'agrega) |

La llista tancada de codis d'ús (`uso_sigpac`) viu al seed `dim_us_sigpac.csv` amb l'etiqueta
en valencià i un flag `es_agrari` (ús agrari productiu vs no agrari, p. ex. vials, aigua,
edificacions, zona urbana). Les 30 classes presents a la CV són un subconjunt de les 33 del
diccionari oficial.

## Peculiaritats conegudes

- Noms de columna del SHP en majúscules i **truncats a 10 caràcters** (DBF).
- `MUNICIPIO` és codi de **catastro**, no INE (vegeu la secció següent).
- Codis especials de catastro `03900/12900/46900` (capitals i zones en litigi).
- ~3,3 milions de polígons: cal processar **sense geometria** (vegeu més avall).

## El codi de municipi de catastro ≠ codi INE

`MUNICIPIO` és el codi de municipi del **Catastro (DGC)**, que **no coincideix amb el codi
INE per a 210 dels 542 municipis** de la CV: hi ha un desfasament sistemàtic a la província
de València (p. ex. catastro `46066` = Beniparrell, però INE `46065`) i codis especials per
a les capitals i els municipis segregats (catastro `12900` = Castelló de la Plana → INE
`12040`; catastro `03126` = Els Poblets → INE `03901`).

Unir per **igualtat directa** `catastro == INE` assignaria silenciosament la superfície de
210 municipis al **municipi equivocat**. Per això s'usa el crosswalk oficial de FEGA
(`xwalk_catastro_ine.csv`, generat per `ingest/sigpac/build_crosswalk.py`), que mapeja els
542 codis de catastro de la CV al seu codi INE. Resolució: **100%** (0 `unresolved`); cap
municipi inventat (default-deny, DATA-PROTECTION.md).

## Privacitat

Els recintes no porten noms de persona. Sí que porten referència cadastral (polígon,
parcel·la, recinte), que **mai es publica a nivell de recinte**: tota la cadena cap als
marts agrega a **municipi × ús**, l'única granularitat publicada. Vegeu DATA-PROTECTION.md.

## Processament memory-safe

Els recintes de la CV són ~3,3 milions de polígons (1.085.000 només a Alacant): carregar-ne
la geometria esgotaria la memòria del build plane (ROADMAP, No-go de la Fase 2). La ingestió
**no toca la geometria**: GDAL llig només la taula d'atributs del SHP dins del `.7z` (via
`/vsi7z/`, GDAL ≥ 3.7, sense cap binari de 7z) i agrega amb el dialecte SQLITE en *streaming*.
Pic mesurat: **~173 MiB de RSS per a tota la CV** (vs diversos GB amb geometria).

## Marts resultants

- `mart_superficie_cultiu_municipi`: superfície (ha) per municipi i ús del sòl.
- `mart_pac_x_superficie_municipi`: diners de la PAC (només jurídiques) × superfície agrària
  per municipi. `import_eur_per_ha` és **orientatiu**: (1) els diners són només de jurídiques
  i la superfície és de tota la terra agrària; (2) FEGA atribueix l'ajuda al municipi de
  **registre** del beneficiari (codi postal), no a on és la terra. Vegeu els cavets al model.

## Reproduir

```sh
uv run python -m ingest.sigpac.download          # baixa els 3 .7z a data/raw/sigpac/ (~1,3 GB)
uv run python -m ingest.sigpac.aggregate         # -> data/raw/sigpac/recintos_agg_2025.csv
# crosswalk catastro -> INE (entrada gitignored: l'Excel de FEGA a data/raw/catastro_ine/):
uv run python -m ingest.sigpac.build_crosswalk   # -> ordit_dbt/seeds/xwalk_catastro_ine.csv
cd ordit_dbt && uv run dbt build
```
