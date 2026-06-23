# Backbone d'entitat canònica per CIF

Pas **additiu** cap a l'Horitzó "entitat al centre". **No refà** l'enllaç de la Fase 3
(`int_enllac`, que connecta FEGA amb cooperatives/SAT per nom): es construeix **al costat**,
keyat per la clau forta que la BDNS ha aportat (el CIF, vegeu [`docs/sources/bdns.md`](sources/bdns.md)).

Models: `int_entitat_cif` (intermediate) → `mart_entitat_canonica` (mart, valencià ASCII).

## Disciplina d'enllaç (com la Fase 3: cap enllaç dur sense base defensable)

| Font | Clau | Tipus d'enllaç |
|------|------|----------------|
| Cooperatives (GVA) | CIF | exacte (dur) |
| BDNS (concessions) | `nif_cif` de persona jurídica | exacte (dur) |
| SAT (GVA) | **sense CIF** (només núm. de registre) | pont per **nom canònic** (`sat_namekey`) cap a un node CIF |

Estats: **confirmat** (≥ 2 fonts corroboren l'entitat), **ambigu** (un SAT el nom del qual casa
amb > 1 CIF: no es col·loca), **unic** (1 sola font). `metode_enllac`: `cif` / `nom` / `cif+nom`.

## Cobertura (BDNS 2023 CV + cooperatives + SAT)

| Mètrica | Valor |
|---------|-------|
| Entitats canòniques | **10.895** |
| — amb CIF | 9.377 |
| — només cooperatives | 5.188 |
| — només BDNS | 4.034 |
| — només SAT (sense CIF recuperat) | 1.518 |
| **confirmat** (≥ 2 fonts) | **155** (148 per CIF exacte coop∩BDNS + 7 SAT per nom) |
| ambigu | 0 |
| unic | 10.740 |
| Euros BDNS al backbone | **2.095 M€** |

Nota: l'overlap coop∩BDNS (148) reflecteix **un sol any** de BDNS (2023). En ingerir més
anys (`just ingest` baixa 2022-2024) creixen tant l'overlap com els euros, sense canviar el
model. El backbone és el teixit connectiu sobre el qual la PAC esdevindrà un atribut més.
