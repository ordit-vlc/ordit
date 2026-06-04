-- Mart: ajudes de la PAC a la Comunitat Valenciana, TOTS els receptors (persones fisiques
-- i juridiques), format llarg per fons. Columnes en valencia ASCII: el renom de l'angles
-- intern al valencia es fa ací, a la capa marts.
--
-- Mode privat (vegeu CLAUDE.md): cap filtre per tipus d'entitat ni anonimitzacio. El
-- llistat es complet, com el de la font. L'anonimitzacio i el compliment legal es faran a
-- una fase dedicada del ROADMAP abans de qualsevol publicacio; ara per ara res no es publica.
--
-- Geografia: municipi i comarca venen de la resolucio CP -> codi_ine -> dim_municipi; els
-- no resolts mantenen el codi_postal pero municipi/comarca son NULL (mai s'inventa cap).
--
-- Format llarg per fons: una fila per (exercici, fons, beneficiari, codi_postal, mesura),
-- amb fons com a dimensio neta {FEAGA, FEADER}. import_eur es l'import del fons. Els
-- imports negatius (recuperacions) son valids i NO es descarten; nomes s'exclouen els zero.
{{ config(materialized="table") }}

with long as (
    select
        beneficiary_name, canonical_key, postal_code, codi_ine, municipi, comarca, provincia,
        measure, financial_year, group_cif, group_name,
        'FEAGA' as fons,
        amount_feaga as import_eur
    from {{ ref("int_fega") }}
    where amount_feaga <> 0

    union all

    select
        beneficiary_name, canonical_key, postal_code, codi_ine, municipi, comarca, provincia,
        measure, financial_year, group_cif, group_name,
        'FEADER' as fons,
        amount_feader as import_eur
    from {{ ref("int_fega") }}
    where amount_feader <> 0
),

-- Etiqueta representativa per clau canonica: la variant del nom d'origen mes FREQUENT (per
-- nombre de files), desempatant per la mes COMPLETA (mes llarga) i despres alfabeticament.
-- Es nomes per a mostrar; el nom d'origen es preserva a cada fila (nom_beneficiari).
representant as (
    select canonical_key, nom_canonic
    from (
        select
            canonical_key,
            beneficiary_name as nom_canonic,
            row_number() over (
                partition by canonical_key
                order by count(*) desc, length(beneficiary_name) desc, beneficiary_name
            ) as rn
        from {{ ref("int_fega") }}
        group by canonical_key, beneficiary_name
    )
    where rn = 1
),

agg as (
    select
        beneficiary_name as nom_beneficiari,
        any_value(canonical_key) as clau_beneficiari,
        any_value(codi_ine) as codi_ine,
        any_value(municipi) as municipi,
        any_value(comarca) as comarca,
        any_value(provincia) as provincia,
        postal_code as codi_postal,
        measure as mesura,
        sum(import_eur) as import_eur,
        fons,
        financial_year as exercici,
        any_value(group_cif) as group_cif,
        any_value(group_name) as group_name
    from long
    group by beneficiary_name, postal_code, measure, fons, financial_year
    having sum(import_eur) <> 0
)

select
    agg.nom_beneficiari,
    agg.clau_beneficiari,
    r.nom_canonic,
    agg.codi_ine,
    agg.municipi,
    agg.comarca,
    agg.provincia,
    agg.codi_postal,
    agg.mesura,
    agg.import_eur,
    agg.fons,
    agg.exercici,
    agg.group_cif,
    agg.group_name
from agg
left join representant r on r.canonical_key = agg.clau_beneficiari
