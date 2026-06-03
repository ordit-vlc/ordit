-- Intermediate de FEGA: parteix el grup (group_cif, group_name) i resol el municipi des
-- del codi postal. Capa interna (anglés ASCII). Porta-ho TOT: cap filtre ni classificacio
-- per tipus d'entitat (mode privat; vegeu CLAUDE.md). Totes les files de FEGA hi son,
-- incloses les persones fisiques amb nom i els codis anonims ES#... tal com arriben de la
-- font (l'anonimitzacio en origen de FEGA no es pot desfer).
--
-- group_raw ("CIF-NOM" del grup) es parteix pel primer "-": la majoria de valors no porten
-- CIF (comencen per "-"), aleshores group_cif queda NULL.
--
-- Normalitzacio de nom (correccio de procedencia, NO fabricacio): alguns beneficiaris venen
-- truncats en origen de FEGA. El crosswalk tracable xwalk_beneficiari corregeix els casos
-- documentats (p. ex. "VALENCIANA" -> "Generalitat Valenciana"); vegeu docs/sources/fega.md.
-- Staging porta el nom tal com arriba (fidel a la font); la correccio s'aplica aci.
{{ config(materialized="table") }}

with prepared as (
    select
        *,
        nullif(split_part(group_raw, '-', 1), '') as group_cif,
        nullif(regexp_replace(group_raw, '^[^-]*-', ''), '') as group_name
    from {{ ref("staging_fega") }}
)

-- Resol postal_code (+ locality_raw de reforç) -> codi_ine -> dim_municipi. La resolucio
-- en dues vies (CP + nom oficial bilingue) viu al seed xwalk_locality (vegeu
-- ingest/geo/build_seeds.py i docs/sources/geografia.md). Els no resolts queden sense
-- municipi (codi_ine NULL), mai s'inventa cap municipi.
select
    p.* replace (coalesce(b.nom_normalitzat, p.beneficiary_name) as beneficiary_name),
    nullif(x.codi_ine, '') as codi_ine,
    coalesce(x.resolved_by, 'unresolved') as geo_resolved_by,
    m.nom as municipi,
    m.comarca,
    -- La provincia ve de l'etiqueta de FEGA (sempre una de les tres per el filtre CV),
    -- no del codi postal (que pot ser d'una provincia veina en municipis de frontera).
    case p.province
        when 'Alacant/Alicante' then 'Alacant'
        when 'Castelló/Castellón' then 'Castelló'
        when 'València/Valencia' then 'València'
    end as provincia
from prepared p
left join {{ ref("xwalk_beneficiari") }} b on b.nom_origen = p.beneficiary_name
left join {{ ref("xwalk_locality") }} x on x.municipi_raw = p.municipality
left join {{ ref("dim_municipi") }} m on m.codi_ine = nullif(x.codi_ine, '')
