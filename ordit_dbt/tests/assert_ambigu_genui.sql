-- Invariant de l'estat: un candidat UNIC es la mateixa entitat (confirmat); l'unica incertesa
-- es l'ambiguitat. Per tant: ambigu => n_candidats > 1, i confirmat => n_candidats = 1. El
-- test passa si no torna res (cap fila viola la regla).
select canonical_key, estat_enllac, metode_enllac, n_candidats
from {{ ref("int_enllac") }}
where (estat_enllac = 'ambigu' and n_candidats <= 1)
   or (estat_enllac = 'confirmat' and n_candidats != 1)
