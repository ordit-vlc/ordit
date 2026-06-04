# Font: BORME (Boletín Oficial del Registre Mercantil)

Nou fil per a l'**spike d'enllaç de la Fase 3** (FEGA × BORME per nom). No és la linkage de
producció: és una llosa acotada per **mesurar la viabilitat** de l'enllaç abans de comprometre
splink ni cap pipeline pesat.

## Procedència

- **Font**: BOE — Datos Abiertos, **BORME Secció A** (Empresaris. Actes inscrits).
- **URL / endpoints** (oficials, JSON + XML):
  - Sumari diari: `https://www.boe.es/datosabiertos/api/borme/sumario/{AAAAMMDD}` (JSON).
  - Acte per província: `https://www.boe.es/diario_borme/xml.php?id=BORME-A-AAAA-NN-PP` (XML),
    on `PP` és el codi de província (03 Alacant, 12 Castelló, 46 València).
- **Cadència**: diària (dies hàbils; caps de setmana i festius no tenen edició → 404).
- **Data de descàrrega**: 2026-06 (llosa de l'spike; el rang és configurable a la ingesta).
- **Llicència**: reutilització permesa de la informació del sector públic (Ley 37/2007; RD
  1495/2011) i avís legal de la BOE. Atribució a la BOE/BORME. **Ús local intern** (build
  plane); en mode privat res no es publica.

## Esquema (parsejat de BORME-A)

El BORME-A és text: `documento/texto/p`. Cada empresa és un paràgraf
`"{núm. full} - {RAÓ SOCIAL}."` seguit dels actes (constitució, nomenaments, cessaments…).
La ingesta extrau només la **identitat d'empresa**:

| camp intern (anglés) | àlies (registre parsejat) | descripció |
|---|---|---|
| `company_name` | `nom` | raó social tal com surt al BORME-A |
| `registry_number` | `num_registre` | número de full registral (abans del ` - `) |
| `province_code` | `provincia` | 03 / 12 / 46 |
| `source_id` | `font_id` | identificador de l'ítem `BORME-A-AAAA-NN-PP` |
| `publication_date` | `data` | data de publicació |

Contracte: [`contracts/borme.py`](../../contracts/borme.py).

## Peculiaritats i limitacions (les diu l'spike)

- **No hi ha CIF/NIF.** El BORME-A només porta el número de full registral i les dades del
  Registre Mercantil, no el CIF. Per això l'enllaç FEGA↔BORME és **només per nom** (cap
  identificador fort). És el risc principal de l'enllaç (ambigüitat per homonímia).
- **Flux d'actes, no instantània del registre.** Una empresa només apareix quan té un acte
  inscrit en la finestra descarregada; ampliar el rang temporal augmenta la cobertura, però
  una empresa sense moviments recents no hi serà. La cobertura mesurada és una **fita
  inferior**, dependent de la finestra.
- **Només Registre Mercantil.** El BORME cobreix **societats de capital** (SL, SA, SLU,
  SAU…). **NO** hi són les **cooperatives** (Registre de Cooperatives), les **SAT** (registre
  especial de Societats Agràries de Transformació), les **CB**/**SC** (comunitats de béns /
  societats civils, sense Registre Mercantil), les **comunitats de regants** ni els
  **organismes públics**. En el cas agroalimentari valencià això és decisiu: bona part dels
  beneficiaris jurídics de la PAC són cooperatives i SAT, **fora de BORME**.
- **Frontera territorial.** La llosa baixa només els registres mercantils de la CV (03/12/46).
  Una empresa valenciana **registrada fora de la CV** (p. ex. domiciliada a Madrid) **no
  eixirà** en esta llosa; l'spike ho ha de tindre present.
- **Forma jurídica escrita.** El BORME sovint escriu la forma sencera (`SOCIEDAD LIMITADA`)
  mentre FEGA usa l'abreviatura (`SL`); la clau canònica no pont eja eixa diferència (vegeu la
  limitació a [`fega.md`](fega.md)). L'spike ho mesura.
