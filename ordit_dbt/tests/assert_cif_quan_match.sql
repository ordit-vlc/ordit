-- Invariant del CIF (nomes cooperatives): tota fila amb font_enllac = 'cooperatives' i
-- estat_enllac = 'match' ha de portar CIF. Les SAT (match) NO porten CIF (la font no en te);
-- per aixo la invariant es especifica de cooperatives. El test passa si no torna res.
select clau_beneficiari, nom_canonic, font_enllac, estat_enllac
from {{ ref("mart_ajudes_pac") }}
where font_enllac = 'cooperatives' and estat_enllac = 'match' and cif is null
