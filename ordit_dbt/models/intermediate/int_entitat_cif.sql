-- Backbone d'entitat canonica per CIF (Horitzo, pas additiu; NO refa l'enllac existent de la
-- Fase 3). Unifica les entitats de les fonts obertes que porten clau forta:
--   - cooperatives (CIF) i BDNS (nif_cif de persona juridica) -> join EXACTE per CIF (dur).
--   - SAT (sense CIF; nomes numero de registre) -> pont per NOM canonic (sat_namekey) cap a
--     un node CIF; confirmat nomes si el nom casa amb UN sol CIF (mateixa disciplina que la
--     Fase 3: cap enllac dur sense base defensable).
--
-- Estat per entitat:
--   confirmat  l'entitat la corroboren >= 2 fonts obertes (CIF exacte coop<->bdns, i/o un
--              SAT que casa univocament per nom).
--   ambigu     un SAT el nom del qual casa amb > 1 CIF: no es pot col.locar (queda node propi).
--   unic       l'entitat nomes apareix en una font (valida, pero sense corroboracio creuada).
--
-- metode_enllac (traçabilitat del COM): 'cif' (coop<->bdns), 'nom' (pont SAT), 'cif+nom', o
-- NULL si no hi ha enllac creuat. Capa interna (angles ASCII); el renom es fa al mart.
{{ config(materialized="view") }}

with coop as (
    select
        upper(trim(cif)) as cif,
        any_value(company_name) as name_coop,
        any_value(registry_key) as registry_key
    from {{ ref("staging_cooperatives") }}
    where nullif(upper(trim(cif)), '') is not null
    group by upper(trim(cif))
),

bdns as (
    select
        nif_cif as cif,
        count(*) as n_concessions_bdns,
        sum(amount_eur) as amount_bdns_eur,
        mode(beneficiary_name) as name_bdns
    from {{ ref("staging_bdns") }}
    where is_legal_person and nif_cif is not null
    group by nif_cif
),

-- Nodes per CIF: union de coop + bdns pel CIF exacte (clau forta, enllac dur defensable).
cif_nodes as (
    select
        coalesce(c.cif, b.cif) as cif,
        coalesce(c.name_coop, b.name_bdns) as canonical_name,
        c.registry_key,
        (c.cif is not null) as in_cooperatives,
        (b.cif is not null) as in_bdns,
        coalesce(b.n_concessions_bdns, 0) as n_concessions_bdns,
        coalesce(b.amount_bdns_eur, 0) as amount_bdns_eur
    from coop c
    full outer join bdns b on b.cif = c.cif
),

cif_nodes_key as (
    select *, {{ sat_namekey('canonical_name') }} as name_key
    from cif_nodes
),

-- Un SAT per numero de registre (la font pot dur variants de nom pel mateix numero; en
-- triem una de determinista). Aixi 'SAT:'||registry_number es clau unica al backbone.
sat as (
    select
        registry_number,
        min(company_name) as name_sat
    from {{ ref("staging_sat") }}
    group by registry_number
),

sat_keyed as (
    select registry_number, name_sat, {{ sat_namekey('name_sat') }} as name_key
    from sat
),

-- Pont SAT -> CIF per nom canonic: compta candidats (confirmat=1, ambigu>1, no-match=0).
sat_bridge as (
    select
        s.registry_number,
        s.name_sat,
        s.name_key,
        count(n.cif) as n_cif_candidats,
        any_value(n.cif) as cif_candidat  -- nomes valid si n_cif_candidats = 1
    from sat_keyed s
    left join cif_nodes_key n on n.name_key = s.name_key and s.name_key is not null
    group by s.registry_number, s.name_sat, s.name_key
),

-- SAT confirmats (1 candidat) agregats per CIF (pot haver-hi mes d'un SAT pel mateix CIF).
sat_confirmat as (
    select
        cif_candidat as cif,
        any_value(registry_number) as sat_registry_number,
        count(*) as n_sat
    from sat_bridge
    where n_cif_candidats = 1
    group by cif_candidat
),

-- 1) Nodes per CIF, enriquits amb el SAT que hi casa univocament.
node_rows as (
    select
        'CIF:' || n.cif as entity_key,
        n.cif,
        n.canonical_name,
        n.registry_key as coop_registry_key,
        sc.sat_registry_number,
        n.in_cooperatives,
        n.in_bdns,
        (sc.cif is not null) as in_sat,
        n.n_concessions_bdns,
        n.amount_bdns_eur,
        cast(0 as bigint) as n_cif_candidats
    from cif_nodes_key n
    left join sat_confirmat sc on sc.cif = n.cif
),

-- 2) SAT que no s'uneixen univocament (0 o >1 candidats): nodes propis sense CIF.
sat_orphan as (
    select
        'SAT:' || registry_number as entity_key,
        cast(null as varchar) as cif,
        name_sat as canonical_name,
        cast(null as varchar) as coop_registry_key,
        registry_number as sat_registry_number,
        false as in_cooperatives,
        false as in_bdns,
        true as in_sat,
        cast(0 as bigint) as n_concessions_bdns,
        cast(0 as double) as amount_bdns_eur,
        n_cif_candidats
    from sat_bridge
    where n_cif_candidats <> 1
),

unified as (
    select * from node_rows
    union all
    select * from sat_orphan
)

select
    entity_key,
    cif,
    canonical_name,
    coop_registry_key,
    sat_registry_number,
    in_cooperatives,
    in_bdns,
    in_sat,
    n_concessions_bdns,
    amount_bdns_eur,
    (in_cooperatives::int + in_bdns::int + in_sat::int) as n_sources,
    case
        when n_cif_candidats > 1 then 'ambigu'
        when (in_cooperatives::int + in_bdns::int + in_sat::int) >= 2 then 'confirmat'
        else 'unic'
    end as link_status,
    case
        when (in_cooperatives and in_bdns) and in_sat then 'cif+nom'
        when in_cooperatives and in_bdns then 'cif'
        when in_sat and (in_cooperatives or in_bdns) then 'nom'
    end as link_method
from unified
