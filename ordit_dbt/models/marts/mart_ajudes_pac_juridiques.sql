-- Mart public: ajudes de la PAC a persones JURIDIQUES de la Comunitat Valenciana.
-- Nomes entity_type == 'legal' (CB/SC ambiguous queden fora; cap persona fisica, mai).
-- Columnes en valencia ASCII (l'esquema public consultable): el renom de l'angles intern
-- al valencia es fa exactament ací, a la capa marts.
--
-- Format llarg per fons: una fila per (exercici, fons, beneficiari, municipi, mesura),
-- amb fons com a dimensio neta {FEAGA, FEADER}. import_eur es l'import del fons (la
-- contribucio europea), sumat per la clau. Els imports negatius (recuperacions) son
-- valids i NO es descarten; nomes s'exclouen els imports exactament zero.
{{ config(materialized="table") }}

with legal as (
    select * from {{ ref("int_fega_classified") }}
    where entity_type = 'legal'
),

long as (
    select
        beneficiary_name, municipality, province, measure, financial_year,
        group_cif, group_name,
        'FEAGA' as fons,
        amount_feaga as import_eur
    from legal
    where amount_feaga <> 0

    union all

    select
        beneficiary_name, municipality, province, measure, financial_year,
        group_cif, group_name,
        'FEADER' as fons,
        amount_feader as import_eur
    from legal
    where amount_feader <> 0
)

select
    beneficiary_name as nom_beneficiari,
    municipality as municipi,
    province as provincia,
    measure as mesura,
    sum(import_eur) as import_eur,
    fons,
    financial_year as exercici,
    any_value(group_cif) as group_cif,
    any_value(group_name) as group_name
from long
group by beneficiary_name, municipality, province, measure, fons, financial_year
having sum(import_eur) <> 0
