-- Coherencia font_enllac <-> estat_enllac: si hi ha enllac (match/possible) hi ha d'haver
-- font (cooperatives/sat); si no-match, la font ha de ser NULL. El test passa si no torna res.
select clau_beneficiari, estat_enllac, font_enllac
from {{ ref("mart_ajudes_pac") }}
where (estat_enllac in ('match', 'possible') and font_enllac is null)
   or (estat_enllac = 'no-match' and font_enllac is not null)
   or (font_enllac is not null and font_enllac not in ('cooperatives', 'sat'))
