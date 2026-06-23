-- Invariant de reconciliacio del backbone: cada euro de BDNS de persona juridica acaba
-- atribuit a una entitat canonica. La suma d'import_bdns_eur al backbone ha de quadrar amb
-- la suma d'amount_eur de staging_bdns per a persones juridiques (les uniques files que
-- aporten CIF i, per tant, node). Tolerancia d'arrodoniment 0.01 EUR. Passa si no torna res.
with backbone as (
    select round(sum(import_bdns_eur), 2) as eur
    from {{ ref("mart_entitat_canonica") }}
),
staging as (
    select round(sum(amount_eur), 2) as eur
    from {{ ref("staging_bdns") }}
    where is_legal_person and nif_cif is not null
)
select
    b.eur as eur_backbone,
    s.eur as eur_staging
from backbone b
cross join staging s
where abs(coalesce(b.eur, 0) - coalesce(s.eur, 0)) > 0.01
