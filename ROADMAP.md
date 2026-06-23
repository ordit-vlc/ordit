# ROADMAP — Ordit

Pla per fases. Cada fase té un lliurable clar i portes go/no-go explícites, a l'estil
de TopQuaranta. No comences una fase abans que la porta anterior estiga verda.

L'ordre està pensat perquè **tota l'ampliació additiva i de qualitat (Fases 4–8) es
puga fer en mode privat, autònom i sense decisió humana**: són fases d'execució amb
portes tècniques (de màquina), no portes humanes. Les **portes humanes** —compliance,
publicació oberta, i les fonts de pagament o de llicència dubtosa— viuen al final, com a
**fases d'investigació/proposta**: el seu lliurable és un informe per a l'humà, no codi
executat. Res no ix del build plane local fins que eixes portes humanes estiguen
superades.

---

## Fase 0 — Fonaments

Objectiu: una base neta, provada i reproduïble abans de cap codi de pipeline.

Lliurable: el scaffold descrit a la secció 9 del CLAUDE.md.

Go:
- `uv sync` funciona, `ruff check` net, `pytest` s'executa (0 proves acceptable).
- `dbt parse` té èxit.
- CI verd al primer PR.
- L'snippet de Caddy per al domini d'Ordit valida al box (warns benignes OK).
- Un fitxer real de FEGA de la Comunitat Valenciana baixat i les seues columnes
  confirmades contra `contracts/fega.py`.

No-go: si el fitxer real de FEGA no casa amb el contracte (columnes, codificació,
agregació a comarca dels municipis xicotets), atura't i reescriu el contracte abans
d'escriure codi de pipeline.

---

## Fase 1 — Ingesta de FEGA

Objectiu: ingerir dades en brut de FEGA i produir un conjunt net i provat. Encara
sense enllaç.

Lliurable:
- Extractor `ingest/fega/` que baixa fitxers de FEGA CV per a 2 o 3 exercicis.
- Validació de contracte passant amb fitxers reals.
- `staging` de dbt + un `mart` de beneficiaris amb TOTS els receptors (mode privat, sense
  filtre per tipus d'entitat: raó social o nom, municipi, mesura, import, fons, exercici).
- Proves de dbt (not null, valors acceptats per a `fons`, claus úniques).

Go: `just build` verd, les proves de dbt passen, el mart té les files esperades per a un
municipi comprovat a mà.

No-go: deriva de contracte entre exercicis que no es pot reconciliar a staging.

---

## Fase 2 — Agregació de SIGPAC

Objectiu: superfície de cultiu per municipi des de SIGPAC, unida a FEGA a nivell de
municipi.

Lliurable:
- `ingest/sigpac/` que baixa la capa SIGPAC CV (GPKG) per a la campanya objectiu.
- `intermediate` de dbt que agrega l'ús i la superfície de cultiu declarats per municipi.
- Un mart que uneix els diners públics de FEGA amb la superfície de cultiu de SIGPAC per
  municipi.

Go: la unió produeix xifres sensates per a un municipi conegut comprovat a mà.

No-go: el fitxer de SIGPAC massa gran per processar al build plane dins de memòria; si
és el cas, passa a processament per trossos o a un box efímer abans de continuar.

---

## Fase 3 — Entity resolution (FEGA x fonts corporatives)

Objectiu: enllaçar els beneficiaris persona jurídica de FEGA amb la seua identitat registral
de manera **determinista i traçable**, per a guanyar identificador fort (CIF o número de
registre) i graf. L'objectiu es manté; el pla concret va canviar després d'un spike.

Spike de viabilitat (FEGA x BORME per nom) → **no-go com a eix**: la secció A del BORME no porta
CIF i només cobreix societats mercantils (SL/SA), mentre que el gros del teixit agrari viu en
altres registres —cooperatives (~43 M€) i SAT (~19 M€). La infraestructura de l'spike queda al
repo i el BORME reapareix a l'Horitzó com a candidat per a la llesca mercantil (ara darrere del
BDNS, que sí porta CIF). No es va descartar: va redirigir l'estratègia cap a un enllaç
determinista sobre els registres on de veres està el teixit.

Lliurable (enllaç **determinista**, no `splink`):
- Clau canònica de beneficiari per **nom** (FEGA no porta CIF), que col·lapsa variants de forma.
- **Directori de Cooperatives** (GVA, CC-BY, amb CIF): enllaç per clau canònica + municipi;
  injecta a FEGA el CIF que no porta.
- **Registre de SAT** (GVA, CC-BY; sense CIF, identificador = número de registre): **nom +
  municipi** són l'autoritat i el número només corrobora (pot estar mal escrit a la font).
- Estats **confirmat / ambigu**: candidat únic → confirmat; ≥ 2 plausibles → ambigu; cap →
  no-match. Amb traçabilitat per enllaç (`metode_enllac`), en lloc del match/possible/no-match
  amb scores del pla original. `splink` queda **diferit** fins que múltiples fonts sorolloses
  generen ambigüitat real.
- Una mostra d'avaluació etiquetada a mà per a mesurar la precisió per font.

Resultat actual: **254 entitats confirmades** (84 cooperatives + 170 SAT), **0 ambigu**.

Go: precisió >= 70% a la mostra etiquetada a mà; el llindar segueix sent condició per a
promoure enllaços al mart.

No-go: si la precisió < 70%, no publiques l'enllaç. Publica primer el conjunt net de
FEGA + SIGPAC (ja valuós) i revisa l'enllaç més avant.

---

# Ampliació additiva (execució autònoma, mode privat)

Les Fases 4–8 són **additives**: afigen fils, marts i qualitat al costat del que ja
existeix, **sense refer res**. Totes les portes són **tècniques (de màquina)** —contractes
que validen, builds i tests verds, cobertura mesurada— i es poden travessar en autònom dins
del build plane local. Cap d'estes fases publica, exposa ni trau dades del build plane.

---

## Fase 4 — Enduriment de qualitat

Objectiu: pujar la confiança en el que ja hi ha abans d'ampliar. Pur additiu sobre els
marts i fils existents (FEGA, SIGPAC, cooperatives, SAT).

Lliurable:
- **Tests de reconciliació**: els totals de cada mart quadren amb els totals de staging
  (cap fila ni cap euro perdut o duplicat pel camí).
- **Tests de dbt que falten** als marts existents: `not_null`, `accepted_values`,
  unicitat de clau, i `relationships` cap a les dimensions.
- **Documentació de fonts** completa a `docs/sources/` per a cada fil actiu (FEGA, SIGPAC,
  cooperatives, SAT): URL, llicència, cadència, data de descàrrega, esquema i peculiaritats
  conegudes.
- **Higiene de CI**: CI dispara també en `push` sobre `main`, perquè cada merge de codi
  duga la seua pròpia execució verda a `main`.

Go: `ruff` + `pytest` + `dbt build` verds amb els tests nous inclosos; tota font activa té
la seua fitxa a `docs/sources/`.

No-go: un test de reconciliació revela una fuga de files o d'euros entre staging i mart;
atura't i quadra-ho abans d'ampliar.

---

## Fase 5 — Capital de fora: BDNS (Base de Datos Nacional de Subvenciones)

Objectiu: incorporar el primer fil de l'eix "capital de fora" de l'Horitzó. La BDNS publica
totes les subvencions públiques espanyoles a nivell d'entitat, amb API; i —el punt crític a
confirmar— amb el NIF/CIF del beneficiari, cosa que FEGA no porta.

### Fase 5a — Spike de contracte BDNS (PORTA TÈCNICA)

Lliurable:
- Un tall **real** de la BDNS (API de `pap.hacienda.gob.es`) per a entitats de la Comunitat
  Valenciana, baixat al build plane.
- `contracts/bdns.py` validat contra el fitxer real.
- `docs/sources/bdns.md` amb la pregunta crítica resolta: **les concessions porten el
  NIF/CIF del beneficiari persona jurídica de manera utilitzable?**

Go: el contracte valida contra el fitxer real i el CIF és present i usable.

No-go: si el contracte no valida o el CIF no és usable, **atura't i informa amb la troballa**
(com l'spike del BORME). No construïsques damunt d'una assumpció dolenta. La infraestructura
de l'spike queda al repo encara que isca no-go.

### Fase 5b — Ingesta i mart BDNS (només si 5a verda)

Lliurable:
- `ingest/bdns/` espillant el patró de FEGA (dada sencera, mode privat, additiu).
- `staging_bdns` + un mart de concessions BDNS per a entitats CV.
- Tests de dbt i de reconciliació com a la Fase 4.

Go: `dbt build` + tests verds; el mart té xifres sensates per a una entitat coneguda.

No-go: deriva d'esquema de l'API que no es pot reconciliar a staging.

---

## Fase 6 — Backbone d'entitat canònica (només si 5a verda i CIF usable)

Objectiu: crear, **al costat** de l'enllaç existent (no refent-lo), un backbone d'entitat
canònica unificada per **CIF**. És el primer pas concret cap a l'Horitzó "entitat al centre",
fet de manera additiva i reversible.

Lliurable:
- Un `intermediate`/`mart` que unifique per CIF les entitats de cooperatives + SAT + BDNS.
- Estats **confirmat / ambigu** amb traçabilitat per enllaç (`metode_enllac`), la mateixa
  disciplina determinista que la Fase 3.
- Informe de cobertura: nombre d'entitats unificades i euros coberts per cada font.

Go: el backbone es construeix amb `dbt build` verd, sense enllaços durs sense base
defensable (candidat únic per CIF), i amb la cobertura informada.

No-go: el CIF de BDNS no enllaça de manera fiable amb el de cooperatives/SAT; en eixe cas,
deixa el backbone com a esborrany documentat i atura't.

---

## Fase 7 — Altres fils oberts CC-BY

Objectiu: reforçar els eixos de valor amb fils **oberts i CC-BY** que no toquen res sensible
ni exigisquen decisió de llicència. Candidat principal: el dataset obert d'**ajudes i
subvencions de la GVA** (tram autonòmic del mateix eix de capital de fora).

Per a cada fil nou, el patró és el mateix i la porta va primer:

1. **Spike de contracte amb fitxer real** (porta tècnica): baixa un tall real, escriu el
   contracte a `contracts/`, valida'l, documenta a `docs/sources/`.
2. Només si valida: **ingest + mart additius**, amb tests i reconciliació.

Go: per cada fil, contracte validat contra fitxer real i `dbt build` + tests verds.

No-go: el contracte no valida → atura eixe fil, informa, i passa al següent fil independent.

Restricció: fonts de **pagament** o amb dada que exigisca una **decisió de llicència**
(SABI, Informa, eInforma, CORPME de pagament) **no s'executen ací** — passen a la fase
d'investigació de fonts del final.

---

## Fase 8 — Catastro i teledetecció

Objectiu: enllaç a nivell de parcel·la i una capa ambiental validada per satèl·lit.

Lliurable:
- Parcel·les de Catastro INSPIRE (geometria, ús) unides a SIGPAC.
- Sèries temporals NDVI de Sentinel-2 per a detecció d'abandó i de dany de la DANA.
- El pont ambiental cap a DTU (aigua, abandó, impacte climàtic sobre els cultius).

Infra: box de Hetzner efímer més gran per al processament de rasters, creat per lot i
destruït. Mai al box de producció.

Go: un senyal reproduïble d'abandó o de dany validat contra una zona coneguda.

---

## Horitzó — L'atles del teixit productiu (direcció diferida, no és una fase)

> Esta secció **no és una fase amb porta go/no-go**: és la direcció a llarg termini decidida,
> registrada ací perquè no es perda. El pla de fases actiu **no canvia** i continuem amb les
> fases vigents. El detall es treballarà quan arribem al pont.
>
> **Nota d'avançament.** Dos candidats d'esta secció ja s'han promogut a fases d'execució
> additives: la **BDNS** (Fase 5) i les **ajudes/subvencions de la GVA** (Fase 7), perquè són
> obertes i no exigeixen cap decisió humana. La resta es manté com a horitzó.

**Visió.** L'objectiu final d'Ordit és un atles del teixit productiu complet del País Valencià,
centrat en les entitats que creen més valor.

**Valor en tres eixos.** El valor d'una entitat es mesura per donar faena (ocupació), generar
beneficis i atraure capital de fora. Amb això, la PAC es reenmarca: és **un** canal d'entrada de
capital exterior entre molts, no l'eix del projecte.

**Reorientació d'arquitectura.** L'eix passa a ser l'**entitat canònica**: una taula d'entitats
on cada font aporta atributs, i la PAC esdevé un atribut més, no la columna vertebral. L'entity
resolution ja feta (clau canònica + enllaços amb CIF o codi de registre) és el teixit connectiu
d'esta reorientació: no es refà, només es reorienta. El backbone de la Fase 6 n'és el primer pas
concret i additiu.

**Panorama de fonts (la realitat oberta/tancada).** El descobriment clau és que els tres eixos
**no estan igual d'oberts**:

- **Capital de fora** — eix ric i obert. La BDNS (Base de Datos Nacional de Subvenciones) publica
  totes les subvencions públiques espanyoles a nivell d'entitat, amb API i —a confirmar en un
  spike— el NIF/CIF del beneficiari, cosa que FEGA no porta. És la primera expansió natural quan
  toque: aporta entitats noves, mesura de capital i clau CIF de colp. Al tram autonòmic, el dataset
  obert de la GVA d'ajudes i subvencions concedides. Candidats europeus a spike: CORDIS, Kohesio
  (FEDER/FSE) i els llistats de Next Generation/PRTR. Capital privat de fora: exportacions
  (Datacomex) i inversió estrangera (DataInvex), però **agregats** per sector i província, no per
  entitat.
- **Ocupació** — mig tancada. L'afiliació a la Seguretat Social ve agregada per municipi i CNAE, no
  per empresa; els empleats per entitat viuen als comptes anuals. Senyal indirecte obert a
  ERO/ERTO i a les ajudes de Labora.
- **Beneficis** — tancada, el coll d'ampolla. La facturació, el benefici i l'actiu són als comptes
  anuals dipositats al Registre Mercantil: legalment públics, però document a document i de pagament
  al CORPME, sense descàrrega massiva oberta. Els agregadors comercials (SABI, Informa, eInforma)
  costen diners i xoquen amb republicar en CC-BY. Caldrà un spike dedicat: ¿hi ha una via compatible
  amb dades obertes a escala, o l'eix "beneficis" es queda en mostra o agregat?

**Matís conceptual.** Captar una subvenció és capital que entra, però no equival a valor de mercat
creat. Convé distingir el capital públic (subvencions: obert) del capital privat o de mercat
(inversió, exportació, benefici: difícil i sovint només agregat).

**Tancament.** És horitzó, no compromís. El detall —inclòs un registre de fonts candidates a
l'estil de `docs/sources` amb banderes oberta?/entitat?/CIF?/llicència/cadència— es farà quan
arribem al pont. De moment, continuem amb el pla de fases vigent.

---

# Fases finals — portes humanes (investigació / proposta)

Les fases següents **no s'executen en autònom**. Toquen dada personal, publicació oberta o
fonts de pagament/llicència dubtosa: són decisions de l'humà com a responsable de les dades.
El **lliurable de cada una és un informe o proposta escrita per a l'humà**, no codi desplegat.
Cap d'estes portes es travessa sense decisió humana explícita, i res no ix del build plane local
fins llavors.

---

## Fase H1 — Compliance i anonimització (investigació/proposta; porta de publicació)

Objectiu: produir el **disseny i la proposta** de la maquinària que convertiria el conjunt
complet (mode privat) en un conjunt publicable. És una **porta dedicada, prèvia i bloquejant**
de qualsevol publicació oberta, outreach o SEO. Mentre el projecte és privat (Fases 1–8) esta
porta no s'activa; ací només es **prepara la proposta**, no s'executa cap filtre ni cap
anonimització sobre les dades.

Lliurable (informe/proposta, no codi desplegat):
- Proposta de **classificació jurídica vs física** (precision-first, default-deny) i de
  **filtre**: només persones jurídiques amb nom i agregats segurs arribarien a la frontera de
  publicació.
- Proposta d'**anonimització** i de **supressió de cel·les xicotetes** (N < 5) als agregats.
- Anàlisi de la **ponderació de l'interés públic** cas per cas (cas Schecke, TJUE C-92/09 i
  C-93/09).
- Especificació d'un **guard de fuga** automàtic (CI + `just publish`): 0 dades de persona
  física a tot artefacte committejat o servit.
- Confirmació que la **frontera de privacitat = frontera build → serve**: el raw i les dades
  personals no ixen mai del build plane local.
- Full de ruta per a la **revisió legal** (DPO/advocat) abans de publicar. Açò no és
  assessorament legal.

Go (humà): l'humà aprova la proposta i decideix activar la implementació en un pas posterior,
amb revisió legal. El codi de referència retirat en passar a mode privat (vegeu `CLAUDE.md` §8
i l'historial de git) es reintroduiria llavors, no ara.

No-go: qualsevol dada personal podria reconstruir-se des dels agregats proposats; cal redissenyar.

---

## Fase H2 — Publicació oberta + explorador (depèn de H1)

Objectiu: publicar dades obertes i un explorador consultable. **Depèn de la Fase H1**: no es
publica res fins que la porta de compliance estiga superada i aprovada per l'humà. En autònom,
el lliurable és només el **disseny** de la publicació, no l'acte de publicar.

Lliurable (disseny + proposta; l'execució requereix go humà):
- Disseny de `publish/` que exportaria els marts a GeoParquet particionat a `data/dist`.
- Pla de servei dels artefactes com a fitxers estàtics darrere de Caddy al serve plane.
- Disseny de l'`explorer/` que consultaria el GeoParquet al navegador amb DuckDB-WASM.
- Identitat visual i UI de l'explorador (handoff de Claude Design a Claude Code), com a proposta.

Go (humà): amb H1 aprovada, l'humà autoritza la publicació; l'explorador carrega i executa una
consulta real contra el GeoParquet publicat, accessible al domini d'Ordit.

No-go: el footprint del serve plane pressiona les apps de producció; si és el cas, la proposta
ha d'allotjar els artefactes en object storage en lloc del box.

---

## Fase H3 — Fonts de pagament i de llicència dubtosa (investigació/proposta)

Objectiu: tancar l'eix "beneficis" de l'Horitzó, que viu en fonts **de pagament o
incompatibles amb CC-BY**. Ací **mai s'ingereix ni s'executa res**: el lliurable és una
proposta escrita per a l'humà.

Lliurable (informe/proposta):
- Anàlisi de viabilitat i de llicència de les fonts de comptes anuals: **CORPME de pagament**,
  i els agregadors comercials **SABI, Informa, eInforma**.
- Resposta a la pregunta de l'Horitzó: ¿hi ha una via compatible amb dades obertes a escala,
  o l'eix "beneficis" es queda en mostra o agregat?
- Recomanació de cost/benefici i de risc de llicència per a la decisió de l'humà.

Go (humà): l'humà decideix, a la vista de la proposta, si s'adquireix alguna font de pagament
i sota quines condicions de llicència. Cap ingesta abans d'eixa decisió.

No-go: cap via compatible amb CC-BY a escala; l'eix "beneficis" es documenta com a limitació
oberta i no s'executa.
