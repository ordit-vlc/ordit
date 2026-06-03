-- Staging de FEGA: neteja els fitxers reals (UTF-8 normalitzat per la ingestio) i els
-- tipa, filtrant a la Comunitat Valenciana. Capa interna: NO es publica i pot portar-ho
-- tot (inclosos noms de persona fisica): mode privat, cap filtre per tipus d'entitat.
--
-- Peculiaritats de la font que es gestionen ací (vegeu docs/sources/fega.md):
--   - coma decimal (format espanyol), sense punt de milers consistent
--   - dates DD/MM/YYYY (sovint buides)
--   - OBJETIVO_ESP multivalor separat per "|"
--   - el ";" final NOMES hi es el 2024 (14 camps) i no el 2025 (13 camps): null_padding
--   - ~1 fila malformada per fitxer (";" incrustat): ignore_errors la salta
--   - l'exercici no ve en cap columna: s'extrau del nom de fitxer
--
-- El glob es configurable via var per a poder validar amb fixtures sintetiques a CI
-- (cap dada de persona fisica entra mai a git ni a CI).
{{ config(materialized="table") }}

with source as (
    select
        *,
        regexp_extract(filename, '_(20[0-9][0-9])[.]utf8', 1)::int as financial_year
    from read_csv(
        '{{ var("fega_raw_glob", "../data/raw/fega/Beneficiarios_municipio_ejercicio_financiero_*.utf8.txt") }}',
        auto_detect = false,
        delim = ';',
        header = true,
        quote = '',
        encoding = 'utf-8',
        columns = {
            'BENEFICIARIO': 'VARCHAR', 'GRUPO_EMPRESA': 'VARCHAR', 'PROVINCIA': 'VARCHAR',
            'MUNICIPIO': 'VARCHAR', 'MEDIDA': 'VARCHAR', 'OBJETIVO_ESP': 'VARCHAR',
            'FEC_INI': 'VARCHAR', 'FEC_FIN': 'VARCHAR', 'FEAGA': 'VARCHAR',
            'FEADER': 'VARCHAR', 'IMPORTECOFIN': 'VARCHAR', 'FEADER_COFIN': 'VARCHAR',
            'IMPORTE_EUROS': 'VARCHAR', '_trailing': 'VARCHAR'
        },
        ignore_errors = true,
        null_padding = true,
        filename = true
    )
    -- Filtre a la Comunitat Valenciana per PROVINCIA (etiqueta bilingue de la font).
    where trim(PROVINCIA) in ('València/Valencia', 'Castelló/Castellón', 'Alacant/Alicante')
)

select
    trim(BENEFICIARIO) as beneficiary_name,
    nullif(trim(GRUPO_EMPRESA), '') as group_raw,
    trim(PROVINCIA) as province,
    nullif(trim(MUNICIPIO), '') as municipality,
    -- MUNICIPIO de FEGA es "codi_postal - nom_localitat" (no codi INE): partim els dos.
    nullif(regexp_extract(MUNICIPIO, '^\s*(\d{5})', 1), '') as postal_code,
    nullif(trim(regexp_replace(MUNICIPIO, '^\s*\d{5}\s*-\s*', '')), '') as locality_raw,
    trim(MEDIDA) as measure,
    list_filter(string_split(OBJETIVO_ESP, '|'), x -> x <> '') as specific_objectives,
    try_strptime(nullif(trim(FEC_INI), ''), '%d/%m/%Y')::date as date_start,
    try_strptime(nullif(trim(FEC_FIN), ''), '%d/%m/%Y')::date as date_end,
    coalesce(try_cast(replace(replace(FEAGA, '.', ''), ',', '.') as decimal(18, 2)), 0) as amount_feaga,
    coalesce(try_cast(replace(replace(FEADER, '.', ''), ',', '.') as decimal(18, 2)), 0) as amount_feader,
    coalesce(try_cast(replace(replace(IMPORTECOFIN, '.', ''), ',', '.') as decimal(18, 2)), 0) as amount_cofin,
    coalesce(try_cast(replace(replace(FEADER_COFIN, '.', ''), ',', '.') as decimal(18, 2)), 0) as amount_feader_cofin,
    coalesce(try_cast(replace(replace(IMPORTE_EUROS, '.', ''), ',', '.') as decimal(18, 2)), 0) as amount_total_eur,
    financial_year
from source
