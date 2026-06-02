-- Unicitat de la clau del mart: (exercici, fons, beneficiari, municipi, mesura).
-- El test passa si no torna cap fila.
select exercici, fons, nom_beneficiari, municipi, mesura, count(*) as n
from {{ ref("mart_ajudes_pac_juridiques") }}
group by 1, 2, 3, 4, 5
having count(*) > 1
