-- Invariant de reconciliacio de BDNS: cap concessio ni cap euro es perd de staging a mart.
-- El mart es una projeccio 1:1 de staging_bdns (renom de columnes, sense agregar ni filtrar),
-- aixi que el nombre de files i la suma d'euros han de coincidir exactament. Tolerancia
-- d'arrodoniment 0.01 EUR. El test passa si no torna cap fila.
with mart as (
    select count(*) as n, round(sum(import_eur), 2) as eur
    from {{ ref("mart_concessions_bdns") }}
),
staging as (
    select count(*) as n, round(sum(amount_eur), 2) as eur
    from {{ ref("staging_bdns") }}
)
select
    m.n as n_mart,
    s.n as n_staging,
    m.eur as eur_mart,
    s.eur as eur_staging
from mart m
cross join staging s
where m.n <> s.n
   or abs(coalesce(m.eur, 0) - coalesce(s.eur, 0)) > 0.01
