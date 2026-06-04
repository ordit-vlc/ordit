-- Invariant de l'estat possible: un 'possible' ha de ser genuinament incert, mai un enllac
-- exacte i unic (que seria un 'match'). Es a dir, possible => aproximat (NO exacte) O ambigu
-- (n_candidats > 1). El test passa si no torna res.
select canonical_key, estat_enllac, enllac_exacte, n_candidats
from {{ ref("int_enllac") }}
where estat_enllac = 'possible' and enllac_exacte and n_candidats = 1
