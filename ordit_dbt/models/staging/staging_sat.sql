-- Staging del Registre de SAT de la Comunitat Valenciana (GVA, CC-BY). Capa interna (angles
-- ASCII), NO publicada. Llig el JSONL ingerit (UTF-8 net; vegeu ingest/sat/download.py i
-- docs/sources/sat.md). El glob es configurable via var per a fixtures sintetiques a CI.
--
-- A diferencia de cooperatives, esta font NO porta CIF; l'identificador registral es el
-- numero de registre.
{{ config(materialized="table") }}

select
    "Nº REGISTRO" as registry_number,
    "DENOMINACIÓN" as company_name,
    "MUNICIPIO" as municipality,
    "PROVÍNCIA" as province_name
from read_json_auto(
    '{{ var("sat_raw_glob", "../data/raw/sat/*.jsonl") }}'
)
where nullif(trim("DENOMINACIÓN"), '') is not null
  and nullif(trim("Nº REGISTRO"), '') is not null
