# Sistema de disseny i explorador d'Ordit

Identitat visual, tokens i components de l'explorador de dades. Prové del handoff de
Claude Design i s'integra ací (mai a l'arrel del repositori). Els fitxers de codi viuen a
`explorer/src/` (`tokens.css`, `base.css`, `components.css`, `explorer.css`, `app.js`).

## Concepte de marca

L'**ordit** són els fils tensats i invisibles del teler (warp, en anglés) que sostenen el
teixit: la metàfora de la infraestructura de dades. Tres regles en deriven:

1. **Sobrietat documental** — paper càlid + tinta freda, com un registre civil. Res
   d'estètica de startup (degradats cridaners, brillantor, rodonesa excessiva).
2. **Veu de màquina** — el monospai (IBM Plex Mono tabular) etiqueta tota dada llegible
   per màquina: capçaleres de taula, valors, codis, metadades.
3. **Arrel ceràmica** — l'accent és un blau cobalt de ceràmica valenciana. Prohibit:
   taronja, paella, falla.

**Procedència sempre visible:** cap dada sense font, data, llicència i estat.

## Tokens

Font de veritat: `explorer/src/tokens.css` (tots en `oklch` per a control perceptual).

- **Superfícies** (paper càlid): `--paper`, `--paper-raised`, `--paper-sunken`, `--paper-inset`.
- **Tinta** (neutre fred): `--ink` (14.8:1, dades), `--ink-2` (7.4:1), `--ink-3` (4.6:1,
  només metadades secundàries), `--ink-4` (mai per a text llegible).
- **Línies**: `--line`, `--line-strong`, `--line-hair`.
- **Accent**: `--blau` i variants; `--blau-tint` per a files actives.
- **Semàntic**: `--ok` (confirmat/match), `--avis` (provisional/possible, ocre, mai
  taronja), `--neutral` (no-match/sense dada, gris), `--err` (error de sistema).
- **Sèries**: `--cat-1…6` (croma constant, varia la tonalitat).
- **Rampa seqüencial**: `--seq-0…6` (per al cartograma, Fase 2).
- **Tipografia**: Spectral (serif, títols/KPI editorials), IBM Plex Sans (interfície),
  IBM Plex Mono (dades). **El serif mai dins l'explorador.**
- **Espaiat** base 4px (`--s-1…10`), radis sobris, focus `--ring` de 3px.

## Components

Definits a `explorer/src/components.css`: `.btn`, `.badge`, `.prov` (insígnia de
procedència), `.card`/`.stat` (KPI en mono tabular), `.field`/`.input`/`.search`,
`.facet`, `.chip`, `.status` (pastilla d'estat, mai només color), `.table-wrap` >
`table.data` (capçalera mono apegalosa, columnes `.num` tabulars, `th.sortable`,
mini-barra `.cellbar`, modificador `.compact`), `.barchart` i `.tilemap` (cartograma).

## Accessibilitat (no negociable)

- Contrast AA+ per a tot el text llegible.
- **El color mai és l'única senyal**: sempre amb etiqueta i/o icona.
- Xifres tabulars de veritat (`tabular-nums` + `tnum`/`lnum`) a taules, KPI i llistes.
- `:focus-visible` amb anell de 3px a tots els controls; facetes operables per teclat.

## L'explorador (v1)

`explorer/index.html` + `explorer/src/app.js`. Tot **client-side**: DuckDB-WASM llig el
Parquet del mart `mart_ajudes_pac` (publicat a `data/dist/` per
`just publish`) i la resta es filtra en memòria.

Estructura:

- **Capçalera apegalosa**: logo, cerca global (beneficiari o municipi), descàrrega CSV.
- **Barra lateral**: facetes de **Exercici**, **Fons**, **Municipi** (amb cerca interna) i
  **Mesura**, amb recomptes; botó *Neteja*.
- **Contingut**: fila de **KPI** (beneficiaris, ajudes, import total, municipis) recalculats
  sobre el filtrat; barra de **vista** (Taula / Gràfic) amb insígnia de procedència;
  **chips** de filtres actius; **taula** ordenable (densitat compacte/còmode) i **gràfic**
  de barres (import per municipi o top receptors).

**Cartograma ajornat:** el `.tilemap` del sistema espera geometria de municipi/comarca;
arriba a la **Fase 2** (unió amb SIGPAC). No s'inventa ara.

## Notes

- Tipografies via Google Fonts (Spectral, IBM Plex Sans/Mono, totes OFL). En producció,
  autoallotjar-les per rendiment i privadesa.
- DuckDB-WASM es carrega des de jsDelivr. Tot és local: no hi ha desplegament ni domini
  públic en esta fase.
