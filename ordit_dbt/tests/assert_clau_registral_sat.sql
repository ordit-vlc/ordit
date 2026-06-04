-- Integritat referencial de SAT: tota clau_registral d'una fila amb font_enllac = 'sat' ha
-- d'existir al registre de SAT (staging_sat.registry_number). El test passa si no torna res.
select m.clau_beneficiari, m.clau_registral
from {{ ref("mart_ajudes_pac") }} m
where m.font_enllac = 'sat'
  and m.clau_registral not in (select registry_number from {{ ref("staging_sat") }})
