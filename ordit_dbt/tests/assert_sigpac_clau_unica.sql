-- Unicitat de la clau del mart de superficie: (codi_ine, codi_us, exercici).
-- El test passa si no torna cap fila.
select codi_ine, codi_us, exercici, count(*) as n
from {{ ref("mart_superficie_cultiu_municipi") }}
group by 1, 2, 3
having count(*) > 1
