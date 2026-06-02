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

# Proves.
test:
    uv run pytest

# Valida la fixture contra els contractes pydantic i la procedencia documentada.
contracts:
    uv run pytest tests/test_contracts.py tests/test_provenance.py

# Executa els extractors -> data/raw (arreplegar les madeixes).
ingest:
    @echo "Sense extractors encara (Fase 1)."

# dbt build: staging -> intermediate -> marts (el teler teixeix).
build:
    cd ordit_dbt && uv run dbt build

# Passada d'entity resolution / nuar (Fase 3+).
link:
    @echo "Sense enllac encara (Fase 3+)."

# Export de marts -> GeoParquet a data/dist (publicar el teixit).
publish:
    @echo "Sense publicacio encara (Fase 4)."

# Serveix l'explorador en local.
serve:
    @echo "Sense explorador encara (Fase 4)."
