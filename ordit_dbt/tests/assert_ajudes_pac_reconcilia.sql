-- Invariant de reconciliacio del cami dels diners FEGA: cap euro es perd ni es duplica de
-- staging a mart. El total per fons de mart_ajudes_pac ha de quadrar amb la suma dels imports
-- corresponents a staging_fega. El mart agrupa i descarta files/grups que sumen zero, pero
-- aixo no canvia el total (el que es descarta sumava zero). Tolerancia d'arrodoniment 0.01 EUR.
-- El test passa si no torna cap fila.
with mart as (
    select fons, round(sum(import_eur), 2) as eur
    from {{ ref("mart_ajudes_pac") }}
    group by fons
),
staging as (
    select 'FEAGA' as fons, round(sum(amount_feaga), 2) as eur from {{ ref("staging_fega") }}
    union all
    select 'FEADER' as fons, round(sum(amount_feader), 2) as eur from {{ ref("staging_fega") }}
)
select
    s.fons,
    s.eur as eur_staging,
    m.eur as eur_mart
from staging s
left join mart m on m.fons = s.fons
where abs(coalesce(m.eur, 0) - s.eur) > 0.01
