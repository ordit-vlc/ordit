-- Invariant de normalitzacio de nom: cap nom truncat del crosswalk xwalk_beneficiari pot
-- sobreviure al mart. Si la correccio de procedencia (a int_fega) s'aplica, cap fila del
-- mart no pot dur encara un nom_beneficiari igual a un nom_origen del crosswalk.
-- El test passa si no torna cap fila.
select m.nom_beneficiari, count(*) as n
from {{ ref("mart_ajudes_pac") }} m
join {{ ref("xwalk_beneficiari") }} b on b.nom_origen = m.nom_beneficiari
group by m.nom_beneficiari
