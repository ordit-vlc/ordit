# Font: Registre de SAT de la Comunitat Valenciana (GVA)

Segona font corporativa de la **Fase 3**. Cobreix les **Societats Agràries de Transformació**
(SAT) d'àmbit valencià (~19 M€, 224 entitats jurídiques de FEGA). **No porta CIF**;
l'identificador registral és el **número de registre**.

## Procedència

- **Font**: Generalitat Valenciana — [dadesobertes.gva.es](https://dadesobertes.gva.es/dataset/mer-soc-agr-transformacio),
  "Sociedades Agrarias de Transformación cuyo ámbito sea la Comunitat Valenciana".
- **URL** (CSV): `https://dadesobertes.gva.es/dataset/78fff61b-22db-42b7-ba17-adf7f22bcbd5/resource/35931fc5-54a5-48cb-953c-3051258acade/download/registro-de-sat-de-la-comunidad-valenciana-.csv`
- **Cadència**: directori complet (snapshot; no flux). ~1.528 SAT.
- **Data de descàrrega**: 2026-06.
- **Llicència**: **CC-BY** (reutilització permesa amb atribució). Ús local intern (build
  plane); en mode privat res no es publica.

## Esquema (columnes de la font)

| camp intern (anglés) | àlies (font) | descripció |
|---|---|---|
| `registry_number` | `Nº REGISTRO` | identificador registral (no CIF) |
| `company_name` | `DENOMINACIÓN` | denominació (sense prefix "SAT" ni número) |
| `status` | `SITUACIÓN` | ALTA / BAJA … |
| `address` | `DOMICILIO SOCIAL` | domicili social |
| `municipality` | `MUNICIPIO` | municipi (desambiguador de l'enllaç) |
| `province_name` | `PROVÍNCIA` | província |
| `postal_code` | `C.P.` | codi postal |
| `num_members` | `Nº SOCIOS` | nombre de socis |

Hi ha més columnes (capital, volum de negocis, objecte, cultius…) que no s'usen ara.
Contracte: [`contracts/sat.py`](../../contracts/sat.py).

## Peculiaritats i limitacions

- **No hi ha CIF/NIF.** L'enllaç amb FEGA és per nom + municipi; s'arrossega el `Nº REGISTRO`
  com a identificador registral.
- **El nom es presenta diferent que a FEGA.** El directori porta la **denominació neta**
  (`SAN RAFAEL 81`) i el `Nº REGISTRO` a banda, mentre que FEGA **encasta** el prefix i el
  número al nom (`SAT 9912 CITRICOS VALENCIANOS`, `SAT N 163 ALBA`, `SAT NUM 8642 D,OR`), de
  forma **inconsistent**. L'enllaç treballa amb un **nucli-SAT** (nom sense `SAT`/`NUM`/`N`/
  `CV`/números) i, a més, casa el número de registre extret del nom de FEGA amb el
  `Nº REGISTRO` del directori.
- **Només àmbit autonòmic.** El directori cobreix les SAT d'**àmbit valencià**; les SAT
  d'**àmbit nacional** (registre del Ministeri, MAPA) **no hi són**. Com que bona part dels
  diners agraris de SAT correspon a SAT grans sovint d'àmbit supra-autonòmic, la cobertura
  per euros és estructuralment baixa (l'spike ho mesura).
- **Municipi en castellà/majúscules** (`SAN RAFAEL DEL RÍO`) vs valencià a FEGA (`Sant Rafel
  del Riu`): el desambiguador per municipi pot fallar en topònims bilingües (compta com a
  possible).
- **Encoding UTF-8 net** (no com cooperatives). ~1 registre malformat (`AGRICOLA TIÃË`)
  d'origen, tolerat: no es repara perquè la resta del fitxer és correcte.
