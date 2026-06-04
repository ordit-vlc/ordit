-- Enllac determinista FEGA <-> Directori de Cooperatives de la CV (Fase 3). Capa interna.
-- Replica en SQL pur la logica de linkage/cooperatives.py (validada a ma, precisio 100% a la
-- mostra etiquetada): clau canonica (canon_beneficiari) + municipi com a desambiguador.
--
-- Estats (ROADMAP Fase 3, mai un enllac dur):
--   match    = clau canonica igual I municipi coincident.
--   possible = clau canonica igual amb municipi distint/sense resoldre, O nucli igual
--              (core_beneficiari, forma juridica fora).
--   no-match = cap candidat.
-- En match/possible arrossega cif i clau registral de la cooperativa (el premi: injecta a
-- FEGA el CIF que no te). Una fila per canonical_key (cobreix TOTS els beneficiaris).
{{ config(materialized="table") }}

with coop as (
    select distinct
        company_name as coop_nom,
        cif,
        registry_key as clau_reg,
        {{ canon_beneficiari("company_name") }} as ck,
        {{ core_beneficiari("company_name") }} as core,
        {{ canon_beneficiari("municipality") }} as muni_ck
    from {{ ref("staging_cooperatives") }}
    where {{ canon_beneficiari("company_name") }} is not null
),

-- Nucli per entitat de FEGA (per a l'estat possible quan la clau exacta no casa).
fega_ent as (
    select canonical_key, any_value({{ core_beneficiari("beneficiary_name") }}) as core
    from {{ ref("int_fega") }}
    group by canonical_key
),
-- Municipis (canonics) de cada entitat de FEGA; en pot tindre diversos.
fega_muni as (
    select distinct canonical_key, {{ canon_beneficiari("municipi") }} as muni_ck
    from {{ ref("int_fega") }}
    where municipi is not null
),

-- Candidats per clau canonica, marcant si el municipi coincideix.
ck_cand as (
    select
        e.canonical_key,
        c.coop_nom,
        c.cif,
        c.clau_reg,
        exists (
            select 1 from fega_muni m
            where m.canonical_key = e.canonical_key and m.muni_ck = c.muni_ck
        ) as muni_ok
    from (select distinct canonical_key from {{ ref("int_fega") }}) e
    join coop c on c.ck = e.canonical_key
),
ck_agg as (
    select
        canonical_key,
        bool_or(muni_ok) as has_muni,
        count(distinct coop_nom) as n_candidats,
        arg_max(cif, muni_ok::int) as cif,
        arg_max(clau_reg, muni_ok::int) as clau_reg
    from ck_cand
    group by canonical_key
),

-- Candidats per nucli (nomes per a entitats sense candidat de clau).
core_cand as (
    select
        e.canonical_key,
        any_value(c.cif) as cif,
        any_value(c.clau_reg) as clau_reg
    from fega_ent e
    join coop c on c.core = e.core and length(e.core) >= 5
    where e.canonical_key not in (select canonical_key from ck_agg)
    group by e.canonical_key
)

select
    k.canonical_key,
    case
        when a.has_muni then 'match'
        when a.canonical_key is not null then 'possible'
        when c.canonical_key is not null then 'possible'
        else 'no-match'
    end as estat_enllac,
    coalesce(a.cif, c.cif) as cif,
    coalesce(a.clau_reg, c.clau_reg) as clau_registral,
    coalesce(a.n_candidats, 0) as n_candidats
from (select distinct canonical_key from {{ ref("int_fega") }}) k
left join ck_agg a on a.canonical_key = k.canonical_key
left join core_cand c on c.canonical_key = k.canonical_key
