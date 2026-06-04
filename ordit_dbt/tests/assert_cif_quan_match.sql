-- Invariant de l'enllac: tota fila amb estat_enllac = 'match' ha de portar CIF (i clau
-- registral). Un match sense CIF seria un enllac incoherent. El test passa si no torna res.
select clau_beneficiari, nom_canonic, estat_enllac
from {{ ref("mart_ajudes_pac") }}
where estat_enllac = 'match' and cif is null
