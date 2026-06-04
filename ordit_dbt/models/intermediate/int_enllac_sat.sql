-- Enllac determinista FEGA <-> Registre de SAT de la CV (Fase 3). Capa interna, font SAT.
--
-- El NUMERO DE REGISTRE es la clau UNICA del registre: dos SAT no poden compartir-lo. FEGA
-- encasta eixe numero al nom ("SAT 9912 CITRICOS"); el directori el porta a banda
-- (Nº REGISTRO). Per aixo el numero de registre coincident es el senyal FORT (match), i el
-- nucli-SAT del nom (sat_core, lossy) es nomes aproximat (possible).
--
-- Estats (ROADMAP Fase 3, mai un enllac dur):
--   match    = numero de registre coincident (clau unica del registre).
--   possible = nomes nucli-SAT del nom igual (aproximat), sense numero coincident.
--   no-match = res.
-- Nomes s'intenta enllacar el subconjunt SAT de FEGA (evita falsos positius del numero en
-- noms no-SAT). SAT no porta CIF: clau_registral = numero de registre.
{{ config(materialized="table") }}

{%- set sat_class = "regexp_matches(upper(strip_accents(beneficiary_name)), '(^|[^A-Z])(SAT)([^A-Z]|$)|SOCIEDAD AGRARIA')" -%}
{%- set regnum = "nullif(regexp_extract(upper(strip_accents(beneficiary_name)), '([0-9][0-9]+)', 1), '')" -%}

with sat as (
    select distinct
        company_name as sat_nom,
        registry_number as num_reg,
        {{ sat_core("company_name") }} as namekey
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

-- Candidats per NUMERO DE REGISTRE (clau unica) -> senyal fort.
reg_agg as (
    select
        e.canonical_key,
        count(distinct s.num_reg) as n_reg,
        any_value(s.num_reg) as num_reg,
        any_value(s.sat_nom) as sat_nom
    from fega_sat e
    join sat s on try_cast(s.num_reg as bigint) = try_cast(e.regnum as bigint)
    where e.regnum is not null
    group by e.canonical_key
),

-- Candidats per nucli-SAT del nom (>=4 caracters) -> aproximat.
name_agg as (
    select
        e.canonical_key,
        count(distinct s.sat_nom) as n_name,
        any_value(s.num_reg) as num_reg,
        any_value(s.sat_nom) as sat_nom
    from fega_sat e
    join sat s on s.namekey = e.namekey and length(e.namekey) >= 4
    group by e.canonical_key
)

select
    k.canonical_key,
    case
        when r.canonical_key is not null then 'match'  -- numero de registre coincident
        when n.canonical_key is not null then 'possible'  -- nucli del nom (aproximat)
        else 'no-match'
    end as estat_enllac,
    coalesce(r.num_reg, n.num_reg) as clau_registral,
    -- exacte = casa pel numero de registre (clau unica); el nucli del nom es aproximat.
    (r.canonical_key is not null) as enllac_exacte,
    coalesce(r.n_reg, n.n_name, 0) as n_candidats
from (select distinct canonical_key from {{ ref("int_fega") }}) k
left join reg_agg r on r.canonical_key = k.canonical_key
left join name_agg n on n.canonical_key = k.canonical_key
