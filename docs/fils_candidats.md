# Registre de fils candidats

Registre de fonts candidates a ingerir, a l'estil de [`docs/sources/`](sources/) però per a
fonts **encara no integrades**. Anticipa el "Tancament" de l'Horitzó del
[`ROADMAP.md`](../ROADMAP.md): banderes oberta? / entitat? / CIF? / llicència / cadència, més
una decisió de **gate** (additiu i independent?) abans de qualsevol ingesta.

La porta de la Fase 7 és doble: (1) el fil ha de ser **obert i CC-BY** i (2) ha de ser
**additiu i independent** (aportar entitats, euros o atributs que no tenim ja). Un fil obert
que duplica una font existent **no passa la porta**.

| Fil | Obert? | Entitat? | CIF? | Llicència | Decisió | Motiu |
|-----|--------|----------|------|-----------|---------|-------|
| Subvencions concedides GVA (tram autonòmic) | Sí | Sí | — | CC-BY | **NO-GO (no additiu)** | Ja cobert per BDNS (vegeu sota) |
| Kohesio (FEDER/FSE, fons UE) | Sí | Sí | dubtós | reutilització lliure UE | **Spike pendent** | Canal de capital UE NO present a BDNS; additiu si l'ID és usable |
| CORDIS (H2020/Horizon Europe) | Sí | Sí | VAT/PIC | reutilització lliure UE | **Spike pendent** | Capital UE de R+D; additiu; cal validar slice CV i ID |
| Operadors ecològics CAECV / DO-IGP (GVA) | Sí | Sí | dubtós | CC-BY (a confirmar) | **Spike pendent** | Atribut de sector/qualitat per a la vertical agroalimentària |
| Datacomex (exportacions) | Sí | **No** | — | reutilització lliure | Diferit | Agregat per sector/província, no per entitat (no enllaça al backbone) |
| DataInvex (inversió estrangera) | Sí | **No** | — | reutilització lliure | Diferit | Agregat, no per entitat |

## NO-GO documentat: subvencions concedides de la GVA (tram autonòmic)

El candidat principal de la Fase 7 era el dataset obert d'ajudes/subvencions concedides de la
GVA. **No passa la porta d'additivitat**: la BDNS (Fase 5, ja ingerida) **ja inclou el tram
autonòmic** de la Comunitat Valenciana, perquè la BDNS s'alimenta precisament d'eixes
publicacions autonòmiques.

Evidència mesurada sobre `mart_concessions_bdns` (CV 2023):

- **7.724 concessions** i **2.012 M€** amb `nivell_administracio = 'AUTONOMICA'` i
  `administracio = 'COMUNITAT VALENCIANA'` — és a dir, el tram GVA ja hi és.
- Ingerir el dataset de la GVA a banda **duplicaria** estes files i afegiria un maldecap de
  reconciliació, sense aportar entitats ni euros nous.

Conclusió: no s'ingereix. Si en el futur es vol el detall de programa/línia que la GVA potser
publica i la BDNS no, seria un **enriquiment** de les files BDNS existents (join per codi de
convocatòria), no un fil nou.

## Spikes additius recomanats (per a l'humà)

Cadascun és un **fil nou amb la seua porta** (spike de contracte amb fitxer real PRIMER,
després ingest només si valida), com es va fer amb la BDNS:

1. **Kohesio (fons de cohesió UE, FEDER/FSE)** — canal de capital que la BDNS no cobreix.
   Exports per país (CSV/XLSX) a `kohesio.ec.europa.eu`. Gate a validar: hi ha slice de la
   Comunitat Valenciana (NUTS ES52) i un identificador d'entitat espanyol (CIF/VAT) usable per
   a enllaçar amb el backbone? La descàrrega passa per la SPA / EU Knowledge Graph (SPARQL),
   no per una URL estàtica simple: cal una sessió d'spike dedicada.
2. **CORDIS (R+D UE)** — beneficiaris de projectes H2020/Horizon Europe, amb VAT/PIC. Additiu
   a l'eix de capital. Gate: slice CV i mapeig VAT→CIF.
3. **Operadors ecològics (CAECV) i DO/IGP** — additius com a **atribut de sector/qualitat** de
   la vertical agroalimentària, no com a euros. Gate: llicència CC-BY i presència de CIF.

Fonts de pagament o de llicència dubtosa (SABI, Informa, eInforma, CORPME de pagament) **no**
entren ací: són la Fase H3 (investigació/proposta), mai execució.
