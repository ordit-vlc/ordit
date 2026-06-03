-- Intermediate de SIGPAC: resol el codi de municipi de catastro a codi_ine i enriqueix
-- amb el nom del municipi, la comarca i l'etiqueta de l'us. Capa interna (anglés ASCII),
-- NO publicada. El renom a valencia es fa al mart.
--
-- Resolucio catastro -> INE: el codi de municipi del Catastro (DGC) NO coincideix amb el
-- codi INE per a 210 dels 542 municipis de la CV (desfasament a Valencia i codis especials
-- per a capitals i municipis segregats). Unir per igualtat assignaria la superficie al
-- municipi equivocat: per aixo s'uneix pel crosswalk oficial de FEGA (xwalk_catastro_ine).
-- Default-deny: el codi de catastro que no estiga al crosswalk queda 'unresolved' (codi_ine
-- NULL), mai s'inventa cap municipi (DATA-PROTECTION.md). La cobertura es una metrica
-- visible (test dbt). Vegeu docs/sources/sigpac.md.
{{ config(materialized="view") }}

select
    s.catastro_code,
    m.codi_ine,
    m.nom as municipi,
    m.comarca,
    m.provincia,
    case when m.codi_ine is not null then 'matched' else 'unresolved' end as geo_resolved,
    s.land_use,
    u.nom_us,
    coalesce(u.es_agrari, false) as is_agrarian,
    s.crop_group,
    s.n_recintes,
    s.surface_m2,
    s.campaign
from {{ ref("staging_sigpac") }} s
left join {{ ref("xwalk_catastro_ine") }} x on x.catastro_code = s.catastro_code
left join {{ ref("dim_municipi") }} m on m.codi_ine = x.codi_ine
left join {{ ref("dim_us_sigpac") }} u on u.codi_us = s.land_use
