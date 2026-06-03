# Fil: Geografia — municipis de la Comunitat Valenciana

Referència geogràfica per a resoldre els codis postals de FEGA a municipis canònics i per
a etiquetar comarca i província. Sense geometria encara (es reserva per a la Fase 2, amb
la llicència de cartografia IGN/ICV traçada).

## Seeds generats

`ingest/geo/build_seeds.py` produeix tres seeds a `ordit_dbt/seeds/`:

| Seed | Contingut | Files |
|------|-----------|-------|
| `dim_municipi.csv` | `codi_ine`, `nom` (valencià), `comarca`, `provincia` | 542 |
| `xwalk_cp_ine.csv` | `postal_code → codi_ine` (via 1) | 618 |
| `xwalk_locality.csv` | cadena `MUNICIPIO` de FEGA → `codi_ine` + `resolved_by` | 1.231 |

## Procedència i llicències

| Material | Font | Llicència |
|----------|------|-----------|
| `codi_ine` (codis de municipi) | INE — Instituto Nacional de Estadística (fets públics) | Domini públic |
| Noms valencians + comarca | Atributs del GeoJSON de municipis (projecte TopQuaranta; toponímia oficial de la GVA), verificats contra INE i contra [`poblacio-valenciana`](https://github.com/) (**CC0**) | Toponímia GVA / verificació CC0 |
| `xwalk_cp_ine` (codi postal → INE) | **GeoNames** (`download.geonames.org/export/zip/ES.zip`), columna `admin3code` | **CC BY 4.0** (atribució a GeoNames) |

> **Atribució GeoNames** (CC BY 4.0): el crosswalk de codis postals deriva de dades de
> [GeoNames](https://www.geonames.org/). La **geometria** dels municipis (Fase 2) encara
> NO s'incorpora: depèn de confirmar i atribuir l'upstream cartogràfic (IGN/ICV).

## Comarcalització (decisió documentada)

La comarca **no és un fet oficial únic**: hi ha diverses comarcalitzacions de la Comunitat
Valenciana. S'ha triat la que porten els atributs del GeoJSON de municipis, de **33
comarques**, que mapeja 1:1 amb cada `codi_ine`. És una elecció de projecte, revisable.

## `MUNICIPIO` de FEGA = codi postal, no codi INE

El camp `MUNICIPIO` de FEGA és `codi_postal - nom_localitat` (p. ex. `46410 - Sueca`), no un
codi INE: un municipi té diversos codis postals (Sueca en té 7). Staging el parteix en
`postal_code` + `locality_raw`.

## Resolució en dues vies (es validen mútuament)

`xwalk_locality.csv` resol cada cadena `MUNICIPIO` distinta de FEGA a `codi_ine` combinant
dues vies independents per clau:

1. **CP → codi_ine** pel crosswalk de GeoNames (via 1).
2. **Nom oficial** → codi_ine, amb àlies bilingüe (valencià GVA + castellà/local INE via
   GeoNames) i maneig de bilingües `X/Y` i de truncament (prefix únic), per al ~28% que
   falla per nom valencià sol (Orihuela, Soneja, "Castelló de la Pla[na]").

Estats (`resolved_by`):

- `both` — les dues vies coincideixen (màxima confiança).
- `cp` / `name` — només una via resol; s'accepta.
- `discrepancy` — les dues vies discrepen → **sense municipi** (default-deny; les
  discrepàncies són errors del crosswalk a inspeccionar).
- `unresolved` — cap via resol → **sense municipi**. **Mai s'inventa cap municipi.**

### Cobertura (exercicis 2024+2025, files de la CV)

| `resolved_by` | Files | % |
|---------------|-------|---|
| `both` | 219.574 | 79% |
| `cp` | 47.756 | 17% |
| `name` | 1.367 | 0,5% |
| `discrepancy` | 3.640 | 1,3% |
| `unresolved` | 3.061 | 1,1% |
| **Resolt (both+cp+name)** | **268.697** | **97,5%** |

Codis postals **many-to-one** (un CP que cobreix >1 municipi): **0** al subconjunt CV de
GeoNames. Al mart de jurídiques, **97,3%** de les files tenen municipi resolt.

## Reproduir

```sh
# 1) Entrades al build plane (gitignored):
#    data/raw/geo/municipis-VAL.json  (atributs del GeoJSON de TopQuaranta)
#    data/raw/geonames/ES.txt         (GeoNames: download.geonames.org/export/zip/ES.zip)
# 2) staging_fega ha d'existir (llig les localitats de FEGA d'allí, no de l'intermediate,
#    per a evitar una dependencia circular amb el seed xwalk_locality):
cd ordit_dbt && uv run dbt build --select staging_fega
cd .. && uv run python -m ingest.geo.build_seeds   # genera els seeds + informe de cobertura
cd ordit_dbt && uv run dbt seed && uv run dbt build
```
