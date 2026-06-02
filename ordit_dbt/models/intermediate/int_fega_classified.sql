-- Intermediate de FEGA: parteix el grup i classifica cada fila per tipus d'entitat.
-- Capa interna (anglés ASCII), NO publicada: classifica TOTHOM, no perd files. El filtre
-- juridica/fisica cap al mart publicable es fa al mart, no ací.
--
-- entity_type (mana el tipus d'entitat, no l'etimologia del nom; precision-first,
-- default-deny; vegeu DATA-PROTECTION.md §9):
--   'natural_masked' : files anonimitzades en origen (BENEFICIARIO = "ES#...").
--   'ambiguous'      : CB (comunitat de bens) / SC (societat civil): personalitat
--                      juridica ambigua; queden FORA del mart en esta fase (ajornat a
--                      la Fase 4). Tenen prioritat sobre 'legal' (mes conservador).
--   'legal'          : forma juridica registrada amb personalitat separada (SL/SLU/SA/
--                      SAU/SAT/SLL/SAL/COOP/SCOOP/S COOP/COOPERATIVA/AIE/fundacio/
--                      associacio), inclosa la forma desplegada.
--   'natural'        : nom de persona sense cap marcador d'entitat.
--
-- group_raw ("CIF-NOM" del grup) es parteix pel primer "-": la majoria de valors no
-- porten CIF (comencen per "-"), aleshores group_cif queda NULL.
{{ config(materialized="table") }}

select
    *,
    nullif(split_part(group_raw, '-', 1), '') as group_cif,
    nullif(regexp_replace(group_raw, '^[^-]*-', ''), '') as group_name,
    case
        when beneficiary_name like 'ES#%' then 'natural_masked'
        when regexp_matches(
            beneficiary_name,
            '(^|[ .,])(S\.?C|C\.?B)\.?([ .,]|$)|SOCIEDAD CIVIL|COMUNIDAD DE BIENES|COMUNITAT DE BENS',
            'i'
        ) then 'ambiguous'
        when regexp_matches(
            beneficiary_name,
            '(^|[ .,])(S\.?L\.?U?|S\.?A\.?U?|S\.?A\.?T|S\.?L\.?L|S\.?A\.?L|S\.?COOP|COOP|COOPERATIVA|A\.?I\.?E)\.?([ .,]|$)'
            || '|SOCIEDAD (DE RESPONSABILIDAD )?LIMITADA|SOCIEDAD ANONIMA'
            || '|SOCIEDAD AGRARIA DE TRANSFORMACION|SOCIEDAD COOPERATIVA'
            || '|AGRUPACION DE INTERES ECONOMICO|FUNDACION|FUNDACIO|ASOCIACION|ASSOCIACIO',
            'i'
        ) then 'legal'
        else 'natural'
    end as entity_type
from {{ ref("staging_fega") }}
