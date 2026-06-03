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
la connexió ja oberta com a `con`. Conté el **raw sencer, incloent-hi persones físiques**,
per a anàlisi interna: explorar, depurar, mesurar cobertura. És **legítim i no està
restringit** (vegeu `DATA-PROTECTION.md` §6).

```sh
just explore-raw
>>> con.sql("show tables")
>>> con.sql("select * from staging_fega limit 5")
```

> **ESTRICTAMENT LOCAL.** Esta DuckDB i el raw viuen només al build plane, gitignored.
> **Mai** es serveix, **mai** s'exposa en cap endpoint i **mai** es posa darrere cap
> protecció (perquè no s'exposa). El que ix cap a fora (publicació, explorador) passa pel
> guard de fuga (`publish/leak_guard.py`): 0 dades de persona física.

## Guard de fuga (frontera build → serve)

Tot artefacte committejat o servit (`data/dist`, seeds, Parquet de l'explorador) es
comprova: 0 codis `ES#...`, 0 files `entity_type != legal` (i, en Fase 3, cap nom
d'administrador del BORME). S'executa a `just publish` i a CI (`tests/test_leak_guard.py`).
Si un artefacte conté dades de persona física, `just publish` peta i esborra el fitxer:
no es publica res brut.

## Desplegament (serve plane)

Caddy multi-tenant: Ordit te el seu snippet a `/etc/caddy/conf.d/*.caddy`, importat pel
Caddyfile mestre. Patro validate-then-rollback + smoke test amb reintents (el mateix que
TopQuaranta i Cercol). _A documentar quan arribe la Fase 4._

## Recuperacio

_A documentar (backups d'artefactes, re-build des de raw)._
