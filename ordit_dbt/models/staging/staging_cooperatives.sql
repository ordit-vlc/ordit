-- Staging del Directori de Cooperatives de la Comunitat Valenciana (GVA, CC-BY). Capa
-- interna (angles ASCII), NO publicada. Llig el JSONL ingerit (ja amb l'encoding reparat;
-- vegeu ingest/cooperatives/download.py i docs/sources/cooperatives.md).
--
-- El glob es configurable via var per a validar amb fixtures sintetiques a CI (cap dada
-- real entra a git ni a CI). A diferencia de FEGA i BORME-A, esta font SI porta CIF.
{{ config(materialized="table") }}

select
    "CD_NIF" as cif,
    "DS_RAZON_SOCIAL" as company_name,
    "CD_CLAVE_REGISTRAL" as registry_key,
    "DS_MUNICIPIO" as municipality,
    "CD_PROVINCIA" as province_code,
    "DS_CLASE" as coop_class
from read_json_auto(
    '{{ var("cooperatives_raw_glob", "../data/raw/cooperatives/*.jsonl") }}'
)
where nullif(trim("DS_RAZON_SOCIAL"), '') is not null
  and nullif(trim("CD_NIF"), '') is not null
