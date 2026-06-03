-- Mart public: superficie SIGPAC per municipi i us del sol, a la Comunitat Valenciana.
-- Columnes en valencia ASCII (l'esquema public consultable); les etiquetes (nom_us,
-- municipi) van en valencia amb accents, com mana CLAUDE.md §5.
--
-- Default-deny geografic: nomes municipis resolts a codi_ine (els 'unresolved' queden
-- fora del mart; la seua cobertura es una metrica visible al test de l'intermediate).
-- La superficie ve agregada per municipi i us. Una fila per (municipi, us, exercici).
{{ config(materialized="table") }}

select
    codi_ine,
    any_value(municipi) as municipi,
    any_value(comarca) as comarca,
    any_value(provincia) as provincia,
    land_use as codi_us,
    any_value(nom_us) as us,
    bool_or(is_agrarian) as es_agrari,
    round(sum(surface_m2) / 10000, 2) as superficie_ha,
    sum(n_recintes) as nombre_recintes,
    campaign as exercici
from {{ ref("int_sigpac_municipi") }}
where geo_resolved = 'matched'
group by codi_ine, land_use, campaign
