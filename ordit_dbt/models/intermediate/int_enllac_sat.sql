-- Enllac determinista FEGA <-> Registre de SAT de la CV (Fase 3). Capa interna, font SAT.
-- Replica en SQL la logica de linkage/sat.py (validada a ma, precisio 100% a la mostra):
-- nucli-SAT del nom (sat_core) + numero de registre extret del nom de FEGA + municipi.
--
-- Nomes s'intenta enllacar el subconjunt SAT de FEGA (evita falsos positius del numero de
-- registre en noms no-SAT). Emet una fila per canonical_key (no-SAT -> no-match). SAT no
-- porta CIF: clau_registral = numero de registre.
{{ config(materialized="table") }}

{%- set sat_class = "regexp_matches(upper(strip_accents(beneficiary_name)), '(^|[^A-Z])(SAT)([^A-Z]|$)|SOCIEDAD AGRARIA')" -%}
{%- set regnum = "nullif(regexp_extract(upper(strip_accents(beneficiary_name)), '([0-9][0-9]+)', 1), '')" -%}

with sat as (
    select distinct
        company_name as sat_nom,
        registry_number as num_reg,
        {{ sat_core("company_name") }} as namekey,
        {{ canon_beneficiari("municipality") }} as muni_ck
    from {{ ref("staging_sat") }}
    where {{ sat_core("company_name") }} is not null
),

-- Entitats SAT de FEGA (nucli-SAT del nom + numero de registre encastat al nom).
fega_sat as (
    select
        canonical_key,
        any_value({{ sat_core("beneficiary_name") }}) as namekey,
        any_value({{ regnum }}) as regnum
    from {{ ref("int_fega") }}
    where {{ sat_class }}
    group by canonical_key
),
fega_muni as (
    select distinct canonical_key, {{ canon_beneficiari("municipi") }} as muni_ck
    from {{ ref("int_fega") }}
    where municipi is not null and {{ sat_class }}
),

-- Candidats per nucli-SAT (>=4 caracters), amb si el municipi coincideix.
name_cand as (
    select
        e.canonical_key, s.sat_nom, s.num_reg,
        exists (
            select 1 from fega_muni m
            where m.canonical_key = e.canonical_key and m.muni_ck = s.muni_ck
        ) as muni_ok
    from fega_sat e
    join sat s on s.namekey = e.namekey and length(e.namekey) >= 4
),
name_agg as (
    select
        canonical_key,
        count(distinct sat_nom) as n_name,
        bool_or(muni_ok) as has_muni,
        arg_max(num_reg, muni_ok::int) as num_reg
    from name_cand
    group by canonical_key
),

-- Candidats per numero de registre (nomes per a entitats sense candidat de nom).
reg_agg as (
    select
        e.canonical_key,
        count(distinct s.sat_nom) as n_reg,
        any_value(s.num_reg) as num_reg
    from fega_sat e
    join sat s on try_cast(s.num_reg as bigint) = try_cast(e.regnum as bigint)
    where e.regnum is not null and e.canonical_key not in (select canonical_key from name_agg)
    group by e.canonical_key
)

select
    k.canonical_key,
    case
        when n.has_muni then 'match'
        when n.canonical_key is not null then 'possible'
        when r.canonical_key is not null then 'possible'
        else 'no-match'
    end as estat_enllac,
    coalesce(n.num_reg, r.num_reg) as clau_registral,
    coalesce(n.n_name, r.n_reg, 0) as n_candidats
from (select distinct canonical_key from {{ ref("int_fega") }}) k
left join name_agg n on n.canonical_key = k.canonical_key
left join reg_agg r on r.canonical_key = k.canonical_key
