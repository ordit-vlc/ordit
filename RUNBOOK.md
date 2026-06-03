# RUNBOOK — Ordit

Operacions: com ingerir, construir, publicar i recuperar. Stub de la Fase 0; s'amplia
a mesura que cada fase entra en servei.

## Plans (seguretat d'ops)

- **Build plane**: maquina local per a les fases 0–3. Box de Hetzner efimer nomes per
  als rasters de satel·lit (fase tardana), creat per lot i destruit.
- **Serve plane**: el CX22 existent. Nomes serveix artefactes finals (GeoParquet
  particionat) com a fitxers estatics darrere de Caddy. **Mai** s'hi executa
  processament pesat: comparteix box amb TopQuaranta + Postgres + l'API de Cercol.

## Posada en marxa (local)

```sh
just setup     # uv sync + pre-commit install
just lint      # ruff check + format --check
just test      # pytest
just build     # dbt build (des de la Fase 1)
```

## Cicle de dades

| Pas | Comanda | Estat |
|-----|---------|-------|
| Arreplegar les madeixes (raw) | `just ingest` | Fase 1 |
| Teixir (staging → marts) | `just build` | Fase 1 |
| Nuar (entity resolution) | `just link` | Fase 3+ |
| Publicar el teixit (GeoParquet) | `just publish` | Fase 4 |
| Servir l'explorador | `just serve` | Fase 4 |
| Explorar el raw sencer en local | `just explore-raw` | sempre |

## Mode raw local (`just explore-raw`)

Obri la DuckDB sencera del build plane (`data/ordit.duckdb`) en una sessió de Python amb
la connexió ja oberta com a `con`. Conté el **raw sencer i tots els receptors, incloent-hi
persones físiques**, per a anàlisi interna: explorar, depurar, mesurar cobertura. En mode
privat (vegeu `CLAUDE.md` §8) es treballa amb les dades completes, sense filtre.

```sh
just explore-raw
>>> con.sql("show tables")
>>> con.sql("select * from staging_fega limit 5")
```

> **ESTRICTAMENT LOCAL.** Esta DuckDB i el raw viuen només al build plane, gitignored.
> **Mai** es serveix ni s'exposa en cap endpoint. Res no ix cap a fora: el projecte és
> privat i no publica. El compliment de protecció de dades (filtre, anonimització, guard de
> fuga) és una fase futura del [`ROADMAP.md`](ROADMAP.md), prèvia a qualsevol publicació.

## Desplegament (serve plane)

Caddy multi-tenant: Ordit te el seu snippet a `/etc/caddy/conf.d/*.caddy`, importat pel
Caddyfile mestre. Patro validate-then-rollback + smoke test amb reintents (el mateix que
TopQuaranta i Cercol). _A documentar quan arribe la Fase 4._

## Recuperacio

_A documentar (backups d'artefactes, re-build des de raw)._
