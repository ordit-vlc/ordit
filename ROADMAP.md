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

Objectiu: enllaçar els beneficiaris persones jurídiques de FEGA amb les fonts corporatives
valencianes per a guanyar identificador fort (CIF) i graf. Un spike de viabilitat (FEGA x
BORME per nom) va mostrar que **BORME tot sol no basta**: només cobreix les societats
mercantils (SL/SA), mentre que la major part dels diners agraris va a **cooperatives** i
**SAT**, en altres registres. Les fonts corporatives són, doncs, **cooperatives + SAT +
BORME**, no BORME en solitari.

Lliurable (per ordre de valor agrari i qualitat d'identificador):
- **Cooperatives de la CV** (GVA, CC-BY, amb CIF): enllaç determinista per clau canònica +
  municipi, ja al teixit (`int_enllac_cooperatives`, columnes `estat_enllac`/`cif`/
  `clau_registral` al mart). Injecta a FEGA el CIF que no porta.
- **SAT de la CV** (GVA, CC-BY) i **BORME multi-any** (BOE): fonts següents.
- La sortida emet **match / possible / no-match** amb traçabilitat per enllaç, mai
  afirmacions dures. `splink` (enllaç probabilístic) queda **diferit**: el matching
  determinista per nom canònic és ja precís; s'avaluarà quan múltiples fonts sorolloses
  generen ambigüitat real.
- Una mostra d'avaluació etiquetada per mesurar la precisió per font.

Go: precisió >= 70% a la mostra etiquetada a mà.

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
