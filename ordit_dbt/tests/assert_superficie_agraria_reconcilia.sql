-- Invariant de reconciliacio: la superficie agraria del creuat per municipi ha de coincidir
-- amb la suma dels usos AGRARIS (es_agrari) del desglossament per municipi i us. Aixi el
-- total "de cultiu" del desglossament a l'explorador quadra amb el llistat i la coropleta;
-- mai s'hi colen els usos no agraris (aigua, urba, improductiu, forestal...).
-- El test passa si no torna cap fila (tolerancia d'arrodoniment 0.01 ha).
with agraris as (
    select codi_ine, round(sum(case when es_agrari then superficie_ha else 0 end), 2) as ha_agraria
    from {{ ref("mart_superficie_cultiu_municipi") }}
    group by codi_ine
)
select
    p.codi_ine,
    p.superficie_agraria_ha,
    a.ha_agraria
from {{ ref("mart_pac_x_superficie_municipi") }} p
join agraris a on a.codi_ine = p.codi_ine
where abs(p.superficie_agraria_ha - a.ha_agraria) > 0.01
