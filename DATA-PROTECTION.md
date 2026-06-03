# Protecció de dades — Ordit

Este document fixa la governança de protecció de dades d'Ordit. És vinculant: cap canvi
de codi, de model o de publicació pot contradir-lo. Si una decisió tècnica xoca amb este
document, mana este document i s'atura la publicació fins a resoldre-ho.

> **Avís.** Això no és assessorament legal. Abans de cap publicació oberta, el conjunt i
> esta política han de ser revisats per una persona delegada de protecció de dades (DPO) o
> un advocat especialista en protecció de dades.

## 1. Finalitat (i només esta)

Ordit existeix per a **derivar estadístiques agregades i un dataset de persones jurídiques
de l'economia productiva valenciana** a partir de fonts públiques. Res més.

Tota funcionalitat, model o publicació que no servisca esta finalitat queda fora d'abast.
No es recopila ni es reté cap dada personal "per si de cas".

## 2. Per què cal cautela encara que la font siga pública

Que una dada siga accessible públicament **no** vol dir que es puga reagregar i
republicar. Republicar i reagregar dades públiques és un **tractament nou** del qual
**Ordit és el responsable** —no la font—, amb les seues pròpies obligacions.

El cas **Schecke** (TJUE, sentència de 9 de novembre de 2010, afers acumulats C-92/09 i
C-93/09) va declarar **desproporcionat** publicar les dades de persones físiques
beneficiàries del FEAGA/FEADER sense ponderar-ho (per exemple, sense distingir per import
o per durada). El FEGA publica avui sota un mandat legal específic i amb anonimització en
origen; **Ordit no té eixe mandat**. Per tant:

> **"És públic" no és "es pot reagregar i republicar".**

La nostra resposta és no tractar mai noms de persona física aigües avall i publicar només
persones jurídiques i agregats segurs.

## 3. Què es publica

- **Persones jurídiques amb nom**: cooperatives, SAT (societats agràries de
  transformació), SL, SA i altres formes societàries clares.
- **Agregats sense nom**: estadístiques per municipi, comarca, mesura, fons, etc.,
  sempre subjectes a la supressió de cel·les xicotetes (§8).

## 4. Què no es publica MAI

- **Cap nom de persona física**, en cap circumstància.
- El **fitxer brut** (raw) de cap font.
- Qualsevol **dada personal**: identificadors, ubicacions a nivell d'individu, imports
  imputables a una persona física, etc.

## 5. Usos prohibits

Ordit **no** es construeix ni es pot usar per a:

- **Perfilar** persones físiques.
- **Buscar o localitzar** individus.
- **Enriquir o enllaçar** persones físiques amb altres dades.

Qualsevol funcionalitat que habilite estos usos és un defecte, no una millora.

## 6. Model operatiu: build plane lliure, frontera de publicació estricta

Açò és el contracte que permet **construir sense por** i **sense relitigar la privacitat a
cada pas**. Hi ha dos plans (vegeu `CLAUDE.md` §2) i una sola frontera que importa.

- **Build plane (local): processa el raw SENCER, incloent-hi persones físiques, per a
  anàlisi interna.** Entendre la dada completa (mirar-la, perfilar-la a nivell agregat,
  depurar-la, mesurar cobertura, explorar la DuckDB sencera) és **legítim i no està
  restringit**. El raw i qualsevol dada personal viuen NOMÉS ací, gitignored: mai a git,
  mai a CI, mai al serve plane.
- **El filtre de persones físiques NOMÉS s'aplica a la frontera de publicació**
  (marts → serve plane). No és una preocupació de cada model intermedi ni de cada commit:
  és un punt únic i ben definit.

> La **frontera build → serve és la frontera de privacitat.** Cap dada personal o sensible
> es committeja al repo, entra a CI ni es serveix: viu només al build plane. El filtre que
> deixa fora les persones físiques es fa exactament en eixa frontera.

Esta separació és el que fa que el treball diari al build plane no haja de demanar permís:
la seguretat la garanteix la frontera (i el guard de fuga, §7), no l'autocensura a cada
passa.

## 7. Arquitectura del filtre i guard de fuga

- El **raw es manté sencer i immutable**: és la procedència; no es retalla en la ingestió.
- La **classificació i el filtre** (jurídica vs física, supressió) es fan a la **capa
  marts**, que és la **frontera de publicació** —**NO** a la ingestió.
- **Staging i intermediate poden portar-ho tot** (inclosos noms de persona física): són
  **interns**, viuen al build plane i **no es publiquen mai**.
- **Minimitza la retenció duradora** aigües avall de noms de persona física: com més prop
  de la frontera de publicació es filtra, menys còpies personals queden.

**Guard de fuga (gate #5 estés a tot el que ix del build plane).** Qualsevol artefacte
**committejat o servit** —`data/dist`, seeds publicables, el Parquet de l'explorador— ha
de contindre **0 dades de persones físiques**: cap codi anònim de FEGA (`ES#...`), cap fila
amb `entity_type != legal` i, quan existisca (Fase 3), cap nom d'administrador del BORME.
És una comprovació automàtica (CI + `just publish`); és el que et deixa construir sense
por. Vegeu `publish/leak_guard.py`.

## 8. Supressió d'agregats

**Agregar no anonimitza si la cel·la és xicoteta.** Una estadística amb pocs beneficiaris
pot aïllar (i, per tant, identificar) un individu.

- Es **suprimeix** tota cel·la agregada amb **menys de N = 5 beneficiaris** (valor
  proposat, revisable per la DPO).
- La supressió s'aplica de manera que cap agregat publicat permeta aïllar un individu
  (atenció també a la supressió secundària: combinacions de cel·les que reconstruirien una
  cel·la suprimida).

**El compliment de publicació és una FASE dedicada, no una preocupació de cada pas.** La
revisió fina —anonimització, supressió de cel·les < N = 5, ponderació de l'interés públic
cas per cas (Schecke, §2), i la revisió legal (DPO/advocat)— es fa **una vegada, com a
porta**, just **abans de qualsevol publicació oberta, outreach o SEO**. Mentre el treball
es queda al build plane (anàlisi, modelatge, exploració), no cal repetir esta revisió a
cada commit: la frontera (§6) i el guard de fuga (§7) ja garanteixen que res personal
n'isca per accident.

## 9. Classificació jurídica vs física

El criteri és **precision-first i default-deny**: davant el dubte, **no es publica**.
**Mana el tipus d'entitat, no l'etimologia del nom.**

- Una entitat amb **forma jurídica registrada** (`SL`, `SLU`, `SA`, `SAU`, `SAT`, `SLL`,
  `SAL`, `COOP`/`SCOOP`/`S COOP`/`COOPERATIVA`, `AIE`, fundació, associació) és **persona
  jurídica i és publicable amb nom**, independentment que el nom continga noms o cognoms
  de persona.
- **No es publiquen amb nom**: les files **emmascarades pel FEGA** (codi `ES#...`) ni els
  **noms de persona sense cap marcador d'entitat**.
- **`CB` (comunitat de béns) i `SC` (societat civil)**: decisió **AJORNADA al moment de
  publicar (Fase 4)**, quan es valore amb dades reals. Ara no es fixa res.

## 10. Retenció

- El **raw no es guarda més enllà del que cal per al build**. Es defineix una **finestra
  de retenció** i, en complir-se, el raw es **refresca o s'esborra**.
- No es conserven còpies de treball amb dades personals fora del build plane ni més enllà
  de la finestra.

## 11. Procedència obligatòria

Cap fet es publica sense una font traçable. Cada font es documenta a
`docs/sources/<fil>.md` (URL, llicència, cadència, data de descàrrega, esquema,
peculiaritats). Vegeu `CLAUDE.md` §5 i §8.

## 12. Llicències

- Codi: MIT (`LICENSE`).
- Dades: CC-BY-4.0 (`LICENSE-DATA`), amb atribució a cada font.

---

Esta política es revisa quan entra una font nova, quan canvia l'abast de publicació o quan
ho indique la revisió legal.
