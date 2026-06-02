# CLAUDE.md — Ordit

Contracte operatiu per a Claude Code en este repositori. Llig-lo sencer abans de
tocar res. Les convencions vénen heretades dels projectes TopQuaranta i Cèrcol i no
són negociables si no és que l'humà les canvia en conversa.

---

## 1. Què és Ordit

Ordit és una infraestructura de dades oberta i autoallotjada per a l'economia
productiva valenciana, construïda íntegrament a partir de fonts públiques. Ingereix,
neteja, enllaça i publica dades rigoroses i llegibles per màquina. La sortida són
dades obertes més un explorador consultable, mai un blog.

La primera vertical és l'agroalimentària (on la dada pública lliure és especialment
rica). L'arquitectura és agnòstica de sector, de manera que verticals posteriors
(indústria, ceràmica, exportació) s'endollen a la mateixa base.

La metàfora del teixit és el vocabulari narratiu del projecte. Mapeja amb la pila
real i és només documentació. Mai ha de crear una estructura paral·lela que es baralle
amb dbt ni amb les eines.

| Terme del teixit | Significat al projecte | Realitat tècnica |
|------------------|------------------------|------------------|
| Ordit (warp) | La infraestructura base | Este monorepo |
| Fil | Una font pública | Una font de dbt (BORME, SIGPAC, Catastro, FEGA, Datacomex, llotja) |
| Madeixa | Dades en brut sense pentinar | Capa raw / landing |
| Teler | El motor que teixeix | ETL + dbt + DuckDB |
| Nuar | Resoldre que dos fils són la mateixa entitat | Entity resolution sobre el graf del BORME |
| Trama | Una vertical teixida damunt l'ordit | Marts de dbt per domini |
| Teixit | El producte visible i publicat | GeoParquet obert + l'explorador |
| Patró | Una versió publicada del conjunt | Un release versionat |

---

## 2. Dos plans (seguretat d'ops)

El box compartit de Hetzner ja executa TopQuaranta + Postgres + l'API de Cèrcol. Una
feina pesada de geo o d'enllaç pot esgotar la memòria d'eixe box i tombar les apps de
producció. Mai executes processament pesat al box de producció.

- Build plane: màquina local per a les fases 0 a 3 (volums modestos). Un box de
  Hetzner efímer més gran, creat per lot i destruït, només quan arriben els rasters de
  satèl·lit (fase tardana).
- Serve plane: el CX22 existent. Només serveix artefactes finals (Parquet/GeoParquet
  particionat) com a fitxers estàtics darrere de Caddy, consultables al navegador amb
  DuckDB-WASM. Footprint mínim, zero risc per a TopQuaranta i Cèrcol.

Caddy segueix el patró multi-tenant existent: Ordit té el seu snippet a
`/etc/caddy/conf.d/*.caddy`, importat pel Caddyfile mestre. Usa el patró de
desplegament validate-then-rollback + smoke test amb reintents que ja s'usa.

---

## 3. Pila

- Python 3.12, gestionat amb `uv`.
- dbt-duckdb (dbt sobre DuckDB), DuckDB amb l'extensió `spatial`.
- pydantic per a contractes de dades i validació.
- splink per a entity resolution probabilística (Fase 3+).
- GDAL/OGR per a ingesta geoespacial (SIGPAC GPKG, Catastro GML/GeoPackage).
- pytest per a proves, ruff per a lint i format (substitueix black + isort).
- `just` com a executor de tasques. Sense binari de CLI propi: dbt + DuckDB + scripts
  ho cobreixen.
- GitHub Actions per a CI.

---

## 4. Disposició del repositori (monorepo)

```
ordit/
├── CLAUDE.md
├── ROADMAP.md
├── README.md              # manifest de cara al públic
├── RUNBOOK.md             # ops: com ingerir, construir, publicar, recuperar
├── LICENSE                # codi: MIT
├── LICENSE-DATA           # dades: CC-BY-4.0
├── pyproject.toml         # projecte uv + ruff + pytest
├── justfile
├── .env.example
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── ingest/                # un mòdul per fil (font)
│   ├── __init__.py
│   ├── fega/
│   └── sigpac/
├── contracts/             # contractes de dades pydantic per font
├── ordit_dbt/             # el teler (projecte dbt)
│   ├── dbt_project.yml
│   ├── profiles.yml       # objectiu duckdb
│   └── models/
│       ├── staging/
│       ├── intermediate/
│       └── marts/
├── linkage/               # entity resolution (splink), Fase 3+
├── publish/               # scripts d'export a GeoParquet
├── explorer/              # explorador DuckDB-WASM, Fase 4 (disseny de Claude Design)
├── data/                  # gitignored: raw/ staging/ dist/
├── docs/
└── tests/                 # pytest
```

Mantín tot en un sol repo. No el partisques fins que el frontend de l'explorador
tinga vida pròpia. Maximitza l'automatització gratuïta, minimitza la complexitat.

---

## 5. Convencions

Llengua (la política d'Ordit): el valencià viu al teixit (allò visible), l'anglés
ASCII a l'ordit (la fontaneria invisible).

L'eix és un de sol: valencià, i si cal una segona llengua, anglés internacional.
Mai el castellà, ni el francés ni l'italià, com a llengua de redacció, de glossa o
de fallback. No s'expliquen mai termes valencians amb el seu equivalent castellà
(p. ex. glossar `ordit` amb `urdimbre`); si un terme necessita aclariment per a un
públic internacional, s'usa el terme anglés (`ordit` = warp). Excepció factual: els
noms de columna de les fonts es documenten tal com els publica la font, encara que
siguen en castellà, perquè això és procedència, no la veu del projecte.

- Valencià amb accents: dades publicades i les seues etiquetes, UI de l'explorador,
  documentació (README, ROADMAP, RUNBOOK, `docs/`), missatges de commit, i comentaris i
  docstrings del codi.
- Valencià ASCII (sense accents ni ç, per a consultes netes): els noms de columna dels
  marts publicats, que són l'esquema públic que la gent consulta.
- Anglés ASCII: identificadors interns (variables, funcions, classes, columnes de
  staging i intermediate), targets del justfile, noms de jobs de CI i noms de variables
  d'entorn. Portabilitat i descobribilitat.
- El renom de l'anglés intern al valencià es fa exactament a la capa marts, el punt on
  la madeixa es torna teixit visible.

Codi:
- Type hints en totes les funcions noves. f-strings. Mai `print()`, usa `logging`.
- ruff per a lint i format. Executa abans de cada commit (pre-commit ho força).
- Tota la configuració i els secrets via variables d'entorn i accés estil
  `python-decouple`. Mai llegisques `os.environ` directament al codi d'aplicació. Un
  sol `.env`, mai commitejat. `.env.example` documenta cada clau.

Proves:
- pytest. Mocka tota crida HTTP externa, mai faces crides de xarxa reals en proves.
- Objectiu de cobertura >= 70% als paquets nucli (`ingest/`, `linkage/`).
- Fixtures: fitxers de mostra xicotets commitejats per a validació de contractes, sense
  claus reals.

Enginyeria de dades:
- Després de canviar models dbt, executa `dbt build` immediatament per aplicar i
  verificar, no al final de la sessió.
- Cada font documentada a `docs/sources/<fil>.md`: URL, llicència, cadència, data de
  descàrrega, esquema, peculiaritats conegudes.
- La procedència és obligatòria. Cap fet es publica sense una font traçable.

Git / PR:
- Obri un PR, no el mergeges fins que l'humà coordine l'ordre.
- Els informes finals indiquen les calibracions explícitament, p. ex. "10/10
  comprovacions verdes després de 2 calibracions (commits abc + def)", incloent
  execucions de CI fallides i els seus commits de correcció.
- Un canvi lògic per PR.

---

## 6. Comandes (justfile)

Els verbs es queden estàndard i avorrits per a descobribilitat de contribuïdors. La
metàfora del teixit (teixir, nuar, arreplegar) viu a la documentació i als comentaris,
no a la interfície de comandes.

```
just setup       # uv sync + pre-commit install
just lint        # ruff check + ruff format --check
just test        # pytest
just contracts   # validar fitxers de mostra contra els contractes pydantic
just ingest      # executar extractors -> data/raw (arreplegar les madeixes)
just build       # dbt build (staging -> intermediate -> marts), el teler teixeix
just link        # passada d'entity resolution / nuar (Fase 3+)
just publish     # export de marts -> GeoParquet a data/dist
just serve       # servir l'explorador en local
```

---

## 7. CI (GitHub Actions)

Replica la divisió de jobs de TopQuaranta i Cèrcol. El verd és obligatori abans de
mergejar.

- `lint`: ruff check + ruff format --check.
- `tests`: pytest. Zero proves és acceptable a la Fase 0.
- `dbt`: `dbt parse` a la Fase 0 (el projecte compila); `dbt build` contra una duckdb
  xicoteta sembrada des de la Fase 1.
- `contracts`: validar fitxers de mostra commitejats contra els contractes pydantic.
  No-op / skip fins que existisca una mostra de la Fase 1.

---

## 8. Governança de dades

- Llicències: codi MIT (`LICENSE`), dades CC-BY-4.0 (`LICENSE-DATA`). Els termes de
  reutilització de FEGA, SIGPAC i Catastro exigeixen atribució; CC-BY és compatible.
  Atribueix cada font a `docs/sources/`.
- RGPD: la publicació oberta conté només persones jurídiques (cooperatives, SAT, SL).
  Les persones físiques queden excloses de tot el que es publica. FEGA ja anonimitza les
  persones físiques per davall de 1.250 EUR i agrega els municipis xicotets a comarca.
- Entity resolution: mai publiques un enllaç dur entre entitats sense un llindar de
  confiança defensable. Emet estats: match / possible / no-match. Un fals "X controla Y"
  sobre diners públics és un passiu, no una funcionalitat. Mantín traçabilitat per
  enllaç.

---

## 9. Scaffold de la Fase 0 (què crear ara)

Crea l'esquelet del repositori de dalt amb:

1. `pyproject.toml` (uv) amb dependències: dbt-duckdb, duckdb, pydantic, pytest, ruff,
   pre-commit. Grup dev: pytest-cov.
2. Config de `ruff` (longitud de línia 100, target py312) i `.pre-commit-config.yaml`
   connectant ruff check + format.
3. `justfile` amb els targets de la secció 6.
4. Projecte dbt `ordit_dbt/` que faça `dbt parse` net amb `staging/`, `intermediate/`,
   `marts/` buits i un `profiles.yml` de duckdb.
5. `.github/workflows/ci.yml` amb `lint`, `tests`, `dbt` (parse). `contracts` present
   però skip.
6. `.env.example`, stub de `RUNBOOK.md`, `docs/sources/` buit, `LICENSE`, `LICENSE-DATA`.
7. `contracts/fega.py` amb el contracte provisional de FEGA de la secció 10.

Go / no-go de la Fase 0:
- `uv sync` funciona, `ruff check` net, `pytest` s'executa (0 proves acceptable).
- `dbt parse` té èxit.
- CI verd al primer PR.
- El definidor real: s'ha baixat un fitxer real de FEGA de la Comunitat Valenciana i
  s'han confirmat les seues columnes contra `contracts/fega.py`. Si no casen, atura't i
  reescriu el contracte abans d'escriure cap codi de pipeline.

---

## 10. Primer contracte de dades: FEGA (provisional)

Provisional fins validar-lo contra un fitxer real descarregat. Els identificadors del
contracte són en anglés ASCII (capa ordit); el renom a columnes valencianes es fa a la
capa marts. Els àlies apunten als noms de columna de la font (provisionals, en castellà)
i confirmar-los és el definidor go/no-go de la Fase 0.

```python
# contracts/fega.py
from pydantic import BaseModel, Field

class FegaBeneficiary(BaseModel):
    """Un registre de transparencia de FEGA. Publicacio oberta: nomes persones juridiques.

    Font: FEGA dades obertes, fitxers de beneficiaris per municipi i exercici. Els
    municipis xicotets s'agreguen a comarca agraria; les persones fisiques per davall de
    1.250 EUR s'anonimitzen en origen.

    Identificadors interns en angles (capa ordit). El renom a columnes valencianes es fa
    a la capa marts. Els alies apunten als noms de columna de la font (provisionals).
    """

    beneficiary_name: str = Field(alias="nombre_beneficiario")        # rao social o etiqueta anonima
    nif: str | None = Field(default=None, alias="nif")                # CIF de persona juridica; None si anonim
    municipality: str | None = Field(default=None, alias="municipio")  # None si s'agrega a comarca
    comarca_agraria: str | None = Field(default=None, alias="comarca_agraria")
    province: str = Field(alias="provincia")
    operation_code: str = Field(alias="codigo_operacion")             # codi de mesura/sector/intervencio
    specific_objective: str | None = Field(default=None, alias="objetivo_especifico")
    amount_eur: float = Field(alias="importe_eur")
    fund: str = Field(alias="fondo")                                  # "FEAGA" o "FEADER"
    financial_year: int = Field(alias="ejercicio")                    # any financer (16 oct n-1 a 15 oct n)
```

La Fase 1 manté només persones jurídiques (`nif` present i no anònim) per als marts
públics. A la capa marts estes columnes es renomenen a valencià ASCII (p. ex.
`beneficiary_name` -> `nom_beneficiari`, `amount_eur` -> `import_eur`, `fund` -> `fons`,
`financial_year` -> `exercici`).
