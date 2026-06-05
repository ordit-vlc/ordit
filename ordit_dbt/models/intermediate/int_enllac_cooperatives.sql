-- Enllac determinista FEGA <-> Directori de Cooperatives de la CV (Fase 3). Capa interna.
--
-- El Registre de Cooperatives certifica DENOMINACIONS UNIQUES (certificacio negativa de
-- denominacio): un nom canonic EXACTE que casa amb UNA sola cooperativa no pot ser una coop
-- distinta, encara que el municipi diferisca (quasi sempre grafia bilingue del MATEIX poble:
-- BICORB/BICORP, Toris/Turis, Xest/Cheste). Per aixo el municipi NO discrimina aci.
--
-- Decisio de l'humà (responsable de les dades): un candidat UNIC es la mateixa entitat
-- (unicitat de denominacio + CIF), tant si casa exacte com per nucli aproximat. L'unica
-- incertesa real es l'ambiguitat (un nom casant amb mes d'una entitat).
-- Estats (ROADMAP Fase 3, mai un enllac dur):
--   confirmat = candidat UNIC (n_candidats = 1), siga exacte o nucli aproximat.
--   ambigu    = n_candidats > 1 (l'unic estat no confirmat).
--   no-match  = cap candidat.
-- metode_enllac registra COM s'ha casat (exacte / nucli) per a auditoria ("cap fet sense font
-- traçable"); no es dubte. Arrossega cif i clau registral (el premi: injecta a FEGA el CIF
-- que no te). Una fila per canonical_key.
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

-- Candidats per clau canonica EXACTA: nombre de cooperatives DISTINTES (per CIF, la clau
-- legal de l'entitat) que comparteixen la clau. Es compta per CIF, no per cadena de nom, aixi
-- una mateixa coop DUPLICADA al directori (mateix CIF, puntuacio distinta) val 1, no 2. El
-- normal es 1 (denominacions uniques); >1 nomes si dos CIF distints comparteixen el nom.
ck_agg as (
    select
        e.canonical_key,
        count(distinct c.cif) as n_candidats,
        any_value(c.cif) as cif,
        any_value(c.clau_reg) as clau_reg
    from (select distinct canonical_key from {{ ref("int_fega") }}) e
    join coop c on c.ck = e.canonical_key
    group by e.canonical_key
),

-- Candidats per nucli (aproximat), nomes per a entitats sense candidat de clau exacta.
-- Tambe es compta per CIF (dedupe del duplicat de font).
core_agg as (
    select
        e.canonical_key,
        count(distinct c.cif) as n_core,
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
        when a.canonical_key is not null and a.n_candidats = 1 then 'confirmat'  -- exacte unic
        when a.canonical_key is not null then 'ambigu'  -- exacte amb >1 candidat
        when c.canonical_key is not null and c.n_core = 1 then 'confirmat'  -- nucli unic
        when c.canonical_key is not null then 'ambigu'  -- nucli amb >1 candidat
        else 'no-match'
    end as estat_enllac,
    coalesce(a.cif, c.cif) as cif,
    coalesce(a.clau_reg, c.clau_reg) as clau_registral,
    -- traçabilitat del COM: exacte (nom canonic) o nucli (core, aproximat).
    case
        when a.canonical_key is not null then 'exacte'
        when c.canonical_key is not null then 'nucli'
    end as metode_enllac,
    -- exacte = casa pel nom canonic exacte (no pel nucli aproximat).
    (a.canonical_key is not null) as enllac_exacte,
    coalesce(a.n_candidats, c.n_core, 0) as n_candidats
from (select distinct canonical_key from {{ ref("int_fega") }}) k
left join ck_agg a on a.canonical_key = k.canonical_key
left join core_agg c on c.canonical_key = k.canonical_key
