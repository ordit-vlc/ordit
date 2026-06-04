-- Enllac corporatiu GENERAL de FEGA (Fase 3): combina les fonts de registre (cooperatives i
-- SAT) en un sol resultat per beneficiari, sense acumular columnes per font. Capa interna.
--
-- Un beneficiari casa amb una sola font segons la seua classe (cooperativa vs SAT), aixi que
-- en la practica son disjunts; si una entitat casara amb totes dues, es tria la de millor
-- estat (match > possible) i, a igualtat, cooperatives (perque aporta CIF).
--
-- Sortida per canonical_key:
--   estat_enllac   match / possible / no-match
--   font_enllac    cooperatives / sat / NULL (no-match)
--   clau_registral clau registral (cooperatives) o numero de registre (SAT)
--   cif            NOMES de cooperatives (identificador fort quan hi es); NULL per SAT
{{ config(materialized="table") }}

with coop as (
    select
        canonical_key, estat_enllac as estat, clau_registral, cif, enllac_exacte, n_candidats,
        case estat_enllac when 'match' then 2 when 'possible' then 1 else 0 end as rang
    from {{ ref("int_enllac_cooperatives") }}
),
sat as (
    select
        canonical_key, estat_enllac as estat, clau_registral, enllac_exacte, n_candidats,
        case estat_enllac when 'match' then 2 when 'possible' then 1 else 0 end as rang
    from {{ ref("int_enllac_sat") }}
)

select
    c.canonical_key,
    -- cooperatives guanya a igualtat de rang (aporta CIF); SAT nomes si te millor rang.
    case
        when c.rang >= s.rang and c.rang > 0 then 'cooperatives'
        when s.rang > 0 then 'sat'
    end as font_enllac,
    case
        when c.rang >= s.rang and c.rang > 0 then c.estat
        when s.rang > 0 then s.estat
        else 'no-match'
    end as estat_enllac,
    case
        when c.rang >= s.rang and c.rang > 0 then c.clau_registral
        when s.rang > 0 then s.clau_registral
    end as clau_registral,
    -- El CIF nomes ve de cooperatives.
    case when c.rang >= s.rang and c.rang > 0 then c.cif end as cif,
    -- exacte i candidats de la font triada (per a l'invariant del possible).
    case
        when c.rang >= s.rang and c.rang > 0 then c.enllac_exacte
        when s.rang > 0 then s.enllac_exacte
        else false
    end as enllac_exacte,
    case
        when c.rang >= s.rang and c.rang > 0 then c.n_candidats
        when s.rang > 0 then s.n_candidats
        else 0
    end as n_candidats
from coop c
join sat s on s.canonical_key = c.canonical_key
