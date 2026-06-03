# Ordit

**La base de dades oberta sobre la qual es teixeix l'economia productiva valenciana.**

Ordit és una infraestructura de dades oberta i autoallotjada, construïda íntegrament
a partir de fonts públiques. Pentina, nua i publica dades rigoroses i llegibles per
màquina sobre la part forta i poc contada de l'economia valenciana.

L'ordit són els fils tensats que sostenen el teixit i que no es veuen al producte
final. Cada
**trama** (agroalimentària hui; indústria, ceràmica i exportació demà) es teixeix
damunt la mateixa base.

- **Fils**: fonts públiques (BORME, SIGPAC, Catastro, FEGA, Datacomex, llotja).
- **Teler**: el pipeline (ETL + dbt + DuckDB).
- **Teixit**: la sortida oberta en GeoParquet i l'explorador.

Dades obertes. En valencià de cara al públic. Com a contribució cultural.

---

## Estat

En construcció. Fase 0 (fonaments). Vegeu [`ROADMAP.md`](ROADMAP.md).

## Com funciona

El detall tècnic i les convencions estan a [`CLAUDE.md`](CLAUDE.md). Les fonts, amb la
seua llicència i procedència, es documenten a `docs/sources/`.

## Estat i protecció de dades

Ordit és ara un projecte **privat i d'un sol usuari**: res no es publica ni s'exposa. Es
treballa amb les dades completes de les fonts públiques per a anàlisi interna. El compliment
de protecció de dades (anonimització, supressió de cel·les xicotetes, filtre de persones
físiques i revisió legal) és una **fase futura dedicada** del [`ROADMAP.md`](ROADMAP.md),
prèvia a qualsevol publicació oberta. Fins llavors, cap dada ix del build plane local.

## Llicència

- Codi: MIT (vegeu [`LICENSE`](LICENSE)).
- Dades: CC-BY-4.0 (vegeu [`LICENSE-DATA`](LICENSE-DATA)) — per a quan es publiquen.

Les dades es deriven de fonts públiques (FEGA, SIGPAC, Catastro i altres), amb atribució a
l'origen.
