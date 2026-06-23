-- Invariant de reconciliacio entre els dos marts de PAC: l'import municipal del creuat
-- (mart_pac_x_superficie_municipi) ha de quadrar amb la suma de mart_ajudes_pac per als
-- mateixos municipis resolts i el mateix exercici (campanya SIGPAC). El creuat parteix de
-- la superficie i fa left join amb les ajudes (codi_ine no nul, exercici = campanya), aixi
-- que el seu total d'euros no pot superar el de mart_ajudes_pac filtrat igual; han de
-- coincidir. Tolerancia d'arrodoniment 0.01 EUR. El test passa si no torna cap fila.
with creuat as (
    select round(sum(import_pac_eur), 2) as eur
    from {{ ref("mart_pac_x_superficie_municipi") }}
),
ajudes as (
    select round(sum(import_eur), 2) as eur
    from {{ ref("mart_ajudes_pac") }}
    where codi_ine is not null
      and exercici = {{ var("sigpac_campaign", 2025) }}
      -- nomes municipis que existeixen al creuat (el creuat parteix de la superficie SIGPAC)
      and codi_ine in (select codi_ine from {{ ref("mart_pac_x_superficie_municipi") }})
)
select
    c.eur as eur_creuat,
    a.eur as eur_ajudes
from creuat c
cross join ajudes a
where abs(coalesce(c.eur, 0) - coalesce(a.eur, 0)) > 0.01
