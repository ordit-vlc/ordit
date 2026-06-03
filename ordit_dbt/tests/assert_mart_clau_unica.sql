-- Unicitat de la clau del mart: (exercici, fons, beneficiari, codi_postal, mesura).
-- El test passa si no torna cap fila.
select exercici, fons, nom_beneficiari, codi_postal, mesura, count(*) as n
from {{ ref("mart_ajudes_pac") }}
group by 1, 2, 3, 4, 5
having count(*) > 1
