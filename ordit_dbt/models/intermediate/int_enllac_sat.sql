-- Enllac determinista FEGA <-> Registre de SAT de la CV (Fase 3). Capa interna, font SAT.
--
-- El NUMERO DE REGISTRE es la clau UNICA del registre: dos SAT no poden compartir-lo. FEGA
-- encasta eixe numero al nom ("SAT 9912 CITRICOS"); el directori el porta a banda
-- (Nº REGISTRO). El numero coincident casa per CODI; el nucli-SAT del nom (sat_core, lossy)
-- casa per NUCLI aproximat. metode_enllac registra el COM (codi / nucli) per a auditoria.
--
-- Decisio de l'humà (responsable de les dades): un candidat UNIC es la mateixa entitat; l'unica
-- incertesa real es l'ambiguitat. Estats (ROADMAP Fase 3, mai un enllac dur):
--   confirmat = candidat UNIC (n_candidats = 1), siga per codi o per nucli.
--   ambigu    = n_candidats > 1 (l'unic estat no confirmat).
--   no-match  = res.
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

-- Candidats per NUMERO DE REGISTRE (clau unica) -> senyal fort. El directori el porta amb
-- sufix d'ambit ("498CV"); FEGA encasta nomes el numero ("498"). Es compara el NUCLI NUMERIC
-- (sense el sufix) als dos costats; clau_registral conserva el valor del directori.
code_cand as (
    select
        e.canonical_key,
        s.num_reg,
        s.sat_nom,
        -- el nucli-SAT de FEGA pot dur el prefix de registre enganxat ("15CVHERMANOSLLOPIS"):
        -- contencio en compte d'igualtat estricta per a desambiguar la colisio de numeros.
        (
            s.namekey is not null and length(s.namekey) >= 4 and length(e.namekey) >= 4
            and (contains(e.namekey, s.namekey) or contains(s.namekey, e.namekey))
        ) as name_ok
    from fega_sat e
    join sat s
        on try_cast(regexp_replace(s.num_reg, '[^0-9]', '', 'g') as bigint)
           = try_cast(e.regnum as bigint)
    where e.regnum is not null
),

-- El nucli numeric pot conflar dos REGISTRES distints (nacional "15" vs autonomic "15CV").
-- Quan passa, el NOM desambigua: si nomes una entrada casa tambe pel nucli-SAT del nom, eixa
-- es la bona (n_reg = 1, confirmat); si cap o mes d'una, queda ambigu (n_reg = n_total).
code_rank as (
    select
        canonical_key, num_reg, sat_nom, name_ok,
        count(*) over (partition by canonical_key) as n_total,
        sum(case when name_ok then 1 else 0 end) over (partition by canonical_key) as n_nameok
    from code_cand
),
reg_agg as (
    select
        canonical_key,
        case when n_total = 1 or n_nameok = 1 then 1 else n_total end as n_reg,
        arg_max(num_reg, case when name_ok then 2 when n_total = 1 then 1 else 0 end) as num_reg,
        arg_max(sat_nom, case when name_ok then 2 when n_total = 1 then 1 else 0 end) as sat_nom
    from code_rank
    group by canonical_key, n_total, n_nameok
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
        when r.canonical_key is not null and r.n_reg = 1 then 'confirmat'  -- codi unic
        when r.canonical_key is not null then 'ambigu'  -- codi amb >1 candidat
        when n.canonical_key is not null and n.n_name = 1 then 'confirmat'  -- nucli unic
        when n.canonical_key is not null then 'ambigu'  -- nucli amb >1 candidat
        else 'no-match'
    end as estat_enllac,
    coalesce(r.num_reg, n.num_reg) as clau_registral,
    -- traçabilitat del COM: codi (numero de registre, clau unica) o nucli (nom aproximat).
    case
        when r.canonical_key is not null then 'codi'
        when n.canonical_key is not null then 'nucli'
    end as metode_enllac,
    -- exacte = casa pel numero de registre (clau unica); el nucli del nom es aproximat.
    (r.canonical_key is not null) as enllac_exacte,
    coalesce(r.n_reg, n.n_name, 0) as n_candidats
from (select distinct canonical_key from {{ ref("int_fega") }}) k
left join reg_agg r on r.canonical_key = k.canonical_key
left join name_agg n on n.canonical_key = k.canonical_key
