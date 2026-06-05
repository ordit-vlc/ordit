-- Enllac determinista FEGA <-> Registre de SAT de la CV (Fase 3). Capa interna, font SAT.
--
-- Principi (decisio de l'humà, responsable de les dades): el NUMERO que FEGA encasta al nom
-- ("SAT 9912 CITRICOS") pot estar MAL ESCRIT, aixi que NO es una clau infal·lible. El senyal
-- mes robust es NOM + MUNICIPI; el numero nomes corrobora. Es puntua cada entrada del directori
-- candidata (nom 4 + numero 2 + municipi 1) i guanya la de millor puntuacio.
--   confirmat = una sola entrada amb la millor puntuacio (la mateixa entitat).
--   ambigu    = empat al cim: >=2 entrades igual de plausibles fins i tot amb nom + municipi.
--   no-match  = cap candidat.
-- metode_enllac registra el COM per a auditoria (codi / nom+municipi / rescat / nucli):
--   codi          el numero corrobora el guanyador (clau de registre coincident).
--   rescat        FEGA duia un numero pero NO casa el guanyador; nom (+municipi) l'han rescatat
--                 (p. ex. ALBOENEA: FEGA diu 577, el registre real es 557CV a Requena).
--   nom+municipi  sense numero a FEGA; casa per nom i municipi.
--   nucli         sense numero ni municipi; casa nomes pel nom (aproximat).
-- Nomes s'intenta enllacar el subconjunt SAT de FEGA. SAT no porta CIF: clau_registral = numero.
{{ config(materialized="table") }}

{%- set sat_class = "regexp_matches(upper(strip_accents(beneficiary_name)), '(^|[^A-Z])(SAT)([^A-Z]|$)|SOCIEDAD AGRARIA')" -%}
{%- set regnum = "nullif(regexp_extract(upper(strip_accents(beneficiary_name)), '([0-9][0-9]+)', 1), '')" -%}
{%- set muni_norm_dir = "nullif(regexp_replace(upper(strip_accents(municipality)), '[^A-Z0-9]', '', 'g'), '')" -%}
{%- set muni_norm_fega = "nullif(regexp_replace(upper(strip_accents(municipi)), '[^A-Z0-9]', '', 'g'), '')" -%}

with dir as (
    select distinct
        company_name as sat_nom,
        registry_number as num_reg,
        try_cast(regexp_replace(registry_number, '[^0-9]', '', 'g') as bigint) as num_core,
        {{ sat_namekey("company_name") }} as namekey,
        {{ muni_norm_dir }} as muni
    from {{ ref("staging_sat") }}
),

-- Entitats SAT de FEGA: clau de nom robusta (tokens ordenats), numero encastat i municipi.
fega as (
    select
        canonical_key,
        any_value({{ sat_namekey("beneficiary_name") }}) as namekey,
        any_value({{ regnum }}) as regnum,
        max({{ muni_norm_fega }}) as muni
    from {{ ref("int_fega") }}
    where {{ sat_class }}
    group by canonical_key
),

-- Candidata si casa pel NOM o pel NUMERO. Es marquen els tres senyals per separat.
cand as (
    select
        f.canonical_key,
        f.regnum as fega_regnum,
        d.num_reg,
        d.sat_nom,
        (f.namekey is not null and length(f.namekey) >= 4 and d.namekey = f.namekey) as name_ok,
        (f.regnum is not null and d.num_core = try_cast(f.regnum as bigint)) as num_ok,
        (
            f.muni is not null and d.muni is not null and length(f.muni) >= 4
            and (contains(d.muni, f.muni) or contains(f.muni, d.muni))
        ) as muni_ok
    from fega f
    join dir d
        on (f.namekey is not null and length(f.namekey) >= 4 and d.namekey = f.namekey)
        or (f.regnum is not null and d.num_core = try_cast(f.regnum as bigint))
),

-- Puntuacio: nom 4 (autoritat) + numero 2 (corroboracio) + municipi 1 (desempat).
scored as (
    select
        *,
        (case when name_ok then 4 else 0 end)
        + (case when num_ok then 2 else 0 end)
        + (case when muni_ok then 1 else 0 end) as score
    from cand
),

-- Per entitat: la millor puntuacio, quantes hi empaten al cim, i la guanyadora (determinista).
ranked as (
    select
        *,
        max(score) over (partition by canonical_key) as best,
        row_number() over (
            partition by canonical_key order by score desc, num_ok desc, num_reg
        ) as rn
    from scored
),
ranked2 as (
    select
        *,
        count(*) filter (where score = best) over (partition by canonical_key) as n_top
    from ranked
),
winner as (
    select * from ranked2 where rn = 1
)

select
    k.canonical_key,
    case
        when w.canonical_key is null then 'no-match'
        when w.n_top = 1 then 'confirmat'
        else 'ambigu'
    end as estat_enllac,
    w.num_reg as clau_registral,
    case
        when w.canonical_key is null then null
        when w.num_ok then 'codi'  -- el numero corrobora la clau de registre
        when w.fega_regnum is not null then 'rescat'  -- numero present pero erroni; nom el rescata
        when w.muni_ok then 'nom+municipi'  -- sense numero; nom + municipi
        else 'nucli'  -- sense numero ni municipi; nomes nom (aproximat)
    end as metode_enllac,
    -- exacte = casa pel numero de registre (clau unica); la resta es per nom (+municipi).
    coalesce(w.num_ok, false) as enllac_exacte,
    coalesce(w.n_top, 0) as n_candidats
from (select distinct canonical_key from {{ ref("int_fega") }}) k
left join winner w on w.canonical_key = k.canonical_key
