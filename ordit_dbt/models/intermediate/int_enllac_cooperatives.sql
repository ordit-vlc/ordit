-- Enllac determinista FEGA <-> Directori de Cooperatives de la CV (Fase 3). Capa interna.
--
-- El Registre de Cooperatives certifica DENOMINACIONS UNIQUES (certificacio negativa de
-- denominacio): un nom canonic EXACTE que casa amb UNA sola cooperativa no pot ser una coop
-- distinta, encara que el municipi diferisca (quasi sempre grafia bilingue del MATEIX poble:
-- BICORB/BICORP, Toris/Turis, Xest/Cheste). Per aixo el municipi NO discrimina aci.
--
-- Estats (ROADMAP Fase 3, mai un enllac dur):
--   match    = nom canonic EXACTE i candidat UNIC (n_candidats = 1), siga quin siga el municipi.
--   possible = NOMES els genuinament incerts: nucli igual (core_beneficiari, aproximat) o un
--              nom canonic exacte que casa amb MES D'UNA cooperativa (n_candidats > 1).
--   no-match = cap candidat.
-- Arrossega cif i clau registral (el premi: injecta a FEGA el CIF que no te). Una fila per
-- canonical_key.
{{ config(materialized="table") }}

with coop as (
    select distinct
        company_name as coop_nom,
        cif,
        registry_key as clau_reg,
        {{ canon_beneficiari("company_name") }} as ck,
        {{ core_beneficiari("company_name") }} as core
    from {{ ref("staging_cooperatives") }}
    where {{ canon_beneficiari("company_name") }} is not null
),

-- Nucli per entitat de FEGA (per a l'estat possible quan la clau exacta no casa).
fega_ent as (
    select canonical_key, any_value({{ core_beneficiari("beneficiary_name") }}) as core
    from {{ ref("int_fega") }}
    group by canonical_key
),

-- Candidats per clau canonica EXACTA: nombre de cooperatives distintes que comparteixen la
-- clau (n_candidats); el normal es 1 (denominacions uniques).
ck_agg as (
    select
        e.canonical_key,
        count(distinct c.coop_nom) as n_candidats,
        any_value(c.cif) as cif,
        any_value(c.clau_reg) as clau_reg
    from (select distinct canonical_key from {{ ref("int_fega") }}) e
    join coop c on c.ck = e.canonical_key
    group by e.canonical_key
),

-- Candidats per nucli (aproximat), nomes per a entitats sense candidat de clau exacta.
core_agg as (
    select
        e.canonical_key,
        count(distinct c.coop_nom) as n_core,
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
        when a.canonical_key is not null and a.n_candidats = 1 then 'match'
        when a.canonical_key is not null then 'possible'  -- exacte pero ambigu (n_candidats > 1)
        when c.canonical_key is not null then 'possible'  -- nucli (aproximat)
        else 'no-match'
    end as estat_enllac,
    coalesce(a.cif, c.cif) as cif,
    coalesce(a.clau_reg, c.clau_reg) as clau_registral,
    -- exacte = casa pel nom canonic exacte (no pel nucli aproximat).
    (a.canonical_key is not null) as enllac_exacte,
    coalesce(a.n_candidats, c.n_core, 0) as n_candidats
from (select distinct canonical_key from {{ ref("int_fega") }}) k
left join ck_agg a on a.canonical_key = k.canonical_key
left join core_agg c on c.canonical_key = k.canonical_key
