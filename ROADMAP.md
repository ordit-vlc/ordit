# ROADMAP — Ordit

Pla per fases. Cada fase té un lliurable clar i portes go/no-go explícites, a l'estil
de TopQuaranta. No comences una fase abans que la porta anterior estiga verda.

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

## Fase C — Compliance i anonimització (porta de publicació)

Objectiu: convertir el conjunt complet (mode privat) en un conjunt publicable. És una
**porta dedicada, prèvia i bloquejant** de qualsevol publicació oberta, outreach o SEO. Es
fa **una sola vegada, no a cada pas**: mentre el projecte és privat (Fases 1-5), es treballa
amb les dades senceres i esta fase no s'activa. Reintrodueix la maquinària que es va retirar
en passar a mode privat (vegeu `CLAUDE.md` §8 i l'historial de git per al codi de referència).

Lliurable:
- Classificació jurídica vs física (precision-first, default-deny) i **filtre**: només
  persones jurídiques amb nom i agregats segurs surten a la frontera de publicació.
- **Anonimització** i **supressió de cel·les xicotetes** (N < 5) als agregats.
- **Ponderació de l'interés públic** cas per cas (cas Schecke, TJUE C-92/09 i C-93/09).
- **Guard de fuga** automàtic (CI + `just publish`): 0 dades de persona física a tot
  artefacte committejat o servit.
- **Frontera de privacitat = frontera build → serve**: el raw i les dades personals no
  ixen mai del build plane local.
- **Revisió legal** (DPO/advocat) abans de publicar. Açò no és assessorament legal.

Go: un artefacte de publicació que passa el guard de fuga amb 0 dades de persona física i la
revisió legal aprovada.

No-go: qualsevol dada personal pot reconstruir-se des dels agregats publicats.

---

## Fase 4 — Publicació oberta + explorador

Objectiu: publicar dades obertes i un explorador consultable. **Depèn de la Fase C**: no es
publica res fins que la porta de compliance estiga superada.

Lliurable:
- `publish/` que exporta els marts a GeoParquet particionat a `data/dist`.
- Artefactes servits com a fitxers estàtics darrere de Caddy al serve plane.
- `explorer/` que consulta el GeoParquet al navegador amb DuckDB-WASM.
- Identitat visual i UI de l'explorador dissenyades a Claude Design, amb handoff a
  Claude Code.

Go: l'explorador carrega, executa una consulta real contra el GeoParquet publicat,
accessible al domini d'Ordit.

No-go: el footprint del serve plane pressiona les apps de producció; si és el cas,
allotja els artefactes en object storage en lloc del box.

---

## Fase 5+ — Catastro i teledetecció

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

**Visió.** L'objectiu final d'Ordit és un atles del teixit productiu complet del País Valencià,
centrat en les entitats que creen més valor.

**Valor en tres eixos.** El valor d'una entitat es mesura per donar faena (ocupació), generar
beneficis i atraure capital de fora. Amb això, la PAC es reenmarca: és **un** canal d'entrada de
capital exterior entre molts, no l'eix del projecte.

**Reorientació d'arquitectura.** L'eix passa a ser l'**entitat canònica**: una taula d'entitats
on cada font aporta atributs, i la PAC esdevé un atribut més, no la columna vertebral. L'entity
resolution ja feta (clau canònica + enllaços amb CIF o codi de registre) és el teixit connectiu
d'esta reorientació: no es refà, només es reorienta.

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
