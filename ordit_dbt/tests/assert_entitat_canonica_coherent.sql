-- Coherencia de l'estat d'enllac del backbone (mateixa disciplina que la Fase 3):
--   - confirmat => l'entitat apareix en >= 2 fonts (n_fonts >= 2).
--   - ambigu    => es un SAT sense CIF (cif IS NULL i en_sat) -> cap enllac dur sense base.
--   - unic      => exactament 1 font.
-- El test passa si no torna cap fila (cap incoherencia).
select clau_entitat, estat_enllac, n_fonts, cif, en_sat
from {{ ref("mart_entitat_canonica") }}
where (estat_enllac = 'confirmat' and n_fonts < 2)
   or (estat_enllac = 'unic' and n_fonts <> 1)
   or (estat_enllac = 'ambigu' and (cif is not null or not en_sat))
