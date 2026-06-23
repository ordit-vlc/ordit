-- Mart: backbone d'entitat canonica per CIF (pas additiu cap a l'Horitzo "entitat al
-- centre"; NO refa l'enllac de la Fase 3). Una fila per entitat canonica: identificada per
-- CIF quan en te (cooperatives + BDNS, join exacte), o per numero de registre SAT quan no
-- (SAT no porta CIF). Columnes en valencia ASCII.
--
-- estat_enllac: confirmat (>= 2 fonts obertes corroboren l'entitat), ambigu (un SAT casa per
-- nom amb > 1 CIF), unic (nomes una font). metode_enllac: cif / nom / cif+nom / NULL. Vegeu
-- int_entitat_cif i docs/sources/bdns.md. Mode privat: dada sencera, res no es publica.
{{ config(materialized="table") }}

select
    entity_key as clau_entitat,
    cif,
    canonical_name as nom_canonic,
    coop_registry_key as clau_registral_coop,
    sat_registry_number as num_registre_sat,
    in_cooperatives as en_cooperatives,
    in_bdns as en_bdns,
    in_sat as en_sat,
    n_sources as n_fonts,
    n_concessions_bdns as n_concessions_bdns,
    round(amount_bdns_eur, 2) as import_bdns_eur,
    link_status as estat_enllac,
    link_method as metode_enllac
from {{ ref("int_entitat_cif") }}
