# Ordit — executor de tasques.
# Verbs estandard i avorrits per a descobribilitat. La metafora del teixit
# (arreplegar madeixes, teixir, nuar) viu nomes als comentaris, mai als noms de target.

# Llista els targets disponibles.
default:
    @just --list

# Prepara l'entorn: dependencies + hooks de git.
setup:
    uv sync
    uv run pre-commit install

# Lint i comprovacio de format (no modifica res).
lint:
    uv run ruff check .
    uv run ruff format --check .

# Proves (amb gate de cobertura sobre ingest/).
test:
    uv run pytest --cov

# Valida les fixtures contra els contractes pydantic i la procedencia documentada.
contracts:
    uv run pytest tests/test_contracts.py tests/test_contracts_sigpac.py tests/test_provenance.py

# Executa els extractors -> data/raw (arreplegar les madeixes). SIGPAC agrega atribut-only
# (sense geometria) i regenera el crosswalk catastro -> INE des de l'Excel de FEGA.
ingest:
    uv run python -m ingest.fega.download
    uv run python -m ingest.sigpac.download
    uv run python -m ingest.sigpac.aggregate
    uv run python -m ingest.sigpac.build_crosswalk

# dbt build: staging -> intermediate -> marts (el teler teixeix).
build:
    cd ordit_dbt && uv run dbt build

# Passada d'entity resolution / nuar (Fase 3+).
link:
    @echo "Sense enllac encara (Fase 3+)."

# Export de marts -> Parquet a data/dist (publicar el teixit).
publish:
    uv run python -m publish.export

# Serveix l'explorador en local (publica primer el Parquet). Nomes local, cap desplegament.
serve: publish
    @echo "Explorador a http://localhost:8000/explorer/  (Ctrl+C per parar)"
    uv run python -m http.server 8000

# Obri la DuckDB SENCERA del build plane (raw incl. persones fisiques) per a exploracio.
# ESTRICTAMENT LOCAL: mai servida, mai en cap endpoint, mai darrere cap proteccio.
explore-raw:
    uv run python -i -c 'import duckdb; con = duckdb.connect("data/ordit.duckdb"); print("Ordit · DuckDB del build plane oberta com a `con` (raw sencer, incl. persones fisiques). Estrictament local. Prova: con.sql(\"show tables\")")'
