# Font: Directori de Cooperatives de la Comunitat Valenciana (GVA)

Primera font corporativa real de la **Fase 3**. A diferència de FEGA i BORME-A, **porta CIF**
(`CD_NIF`): en enllaçar amb FEGA injecta el CIF que FEGA no té. Cobreix el tros agrari més
gran (cooperatives, ~43 M€, 182 entitats jurídiques de FEGA).

## Procedència

- **Font**: Generalitat Valenciana — [dadesobertes.gva.es](https://dadesobertes.gva.es/dataset/soc-cooperativas-2023),
  "Directorio de Cooperativas de la Comunitat Valenciana" (Registre de Cooperatives de la CV).
  Catalogat també a [datos.gob.es](https://datos.gob.es/en/catalogo/a10002983-directorio-de-cooperativas-de-la-comunitat-valenciana-2025).
- **URL** (snapshot 2025, CSV): `https://dadesobertes.gva.es/dataset/ac050833-9d08-40f5-bb7e-027db6347682/resource/e20d8485-cfd7-48e0-8ebc-a5a5bb69b230/download/cooperativas-valencianas_202501.csv`
- **Cadència**: snapshot **anual** (directori complet, no flux); disponibles 2020→2025.
- **Data de descàrrega**: 2026-06 (snapshot 2025; ~8.000 cooperatives de la CV).
- **Llicència**: **CC-BY** (Creative Commons Reconeixement) — reutilització permesa amb
  atribució. Ús local intern (build plane); en mode privat res no es publica.

## Esquema (columnes de la font)

| camp intern (anglés) | àlies (font) | descripció |
|---|---|---|
| `cif` | `CD_NIF` | NIF/CIF de la cooperativa (**el premi de l'enllaç**) |
| `company_name` | `DS_RAZON_SOCIAL` | raó social |
| `registry_key` | `CD_CLAVE_REGISTRAL` | clau registral (p. ex. `V-3251`) |
| `address` | `DS_DOMICILIO` | domicili social |
| `province_code` / `province_name` | `CD_PROVINCIA` / `DS_PROVINCIA` | 03/12/46 |
| `municipality_code` / `municipality` | `CD_MUNICIPIO` / `DS_MUNICIPIO` | municipi (desambiguador de l'enllaç) |
| `coop_class` | `DS_CLASE` | classe (p. ex. TRABAJO ASOCIADO) |

Contracte: [`contracts/cooperatives.py`](../../contracts/cooperatives.py).

## Peculiaritats

- **Encoding doble-mojibake.** El CSV és UTF-8 **doble-codificat** (p. ex. `VALENCIAÃˆ` per
  `VALÈNCIA`, `NÂº` per `Nº`). La ingesta el repara per caràcter (recupera el byte intern
  amb cp1252, després latin-1, i torna a descodificar UTF-8); vegeu `repair_mojibake` a
  `ingest/cooperatives/download.py`. Verificat: 0 residus de mojibake en tot el fitxer.
- **Codi de província inconsistent** (`03` i `3` per a Alacant); s'usa el nom de municipi
  canonicalitzat com a desambiguador de l'enllaç, no el codi.
- **Directori, no flux.** És la llista completa vigent de cooperatives de la CV: la cobertura
  no està limitada per finestra (a diferència de BORME).
- **Totes les classes.** Inclou totes les cooperatives (treball associat, agràries, habitatge…),
  no només agràries; l'enllaç amb FEGA és per nom canònic + municipi, independent de la classe.

## Enllaç al teixit

L'enllaç determinista FEGA ↔ cooperatives viu dins de dbt: `staging_cooperatives` (capa
interna) → `int_enllac_cooperatives` (clau canònica + municipi, estat match/possible/no-match)
→ columnes `estat_enllac`, `cif` i `clau_registral` al mart `mart_ajudes_pac`. Es poblen per
match i possible (mai un enllaç dur); no-match deixa `cif`/`clau_registral` nul·les i preserva
tots els receptors. L'eina de mesura reusable és `linkage/cooperatives.py` (`just
link-cooperatives`).

