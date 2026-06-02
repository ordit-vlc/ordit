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

## Llicència

- Codi: MIT (vegeu [`LICENSE`](LICENSE)).
- Dades: CC-BY-4.0 (vegeu [`LICENSE-DATA`](LICENSE-DATA)).

Les dades es deriven de fonts públiques (FEGA, SIGPAC, Catastro i altres) i es publiquen
amb atribució a l'origen. Ordit no publica dades de persones físiques.
