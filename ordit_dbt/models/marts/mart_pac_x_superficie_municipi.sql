-- Mart public: diners de la PAC (persones juridiques) creuats amb la superficie agraria
-- de SIGPAC, per municipi de la Comunitat Valenciana. Un indicador municipal d'intensitat
-- d'ajuda per hectarea. Columnes en valencia ASCII.
--
-- CAVETS (documentats, no defectes; cal interpretar import_eur_per_ha amb cura):
--   1. L'import es NOMES de persones juridiques (l'unic publicable; DATA-PROTECTION.md),
--      mentre que la superficie agraria de SIGPAC es de TOTA la terra agraria del municipi.
--      Per tant import_eur_per_ha es "euros de PAC de juridiques per hectarea agraria
--      total", NO l'ajuda total per hectarea.
--   2. FEGA atribueix l'ajuda al municipi de REGISTRE del beneficiari (codi postal), no a
--      on es fisicament la terra. Una cooperativa gran registrada en un poble xicotet pot
--      donar un euros/ha desorbitat (diners alts sobre poca superficie local). L'indicador
--      es municipal i orientatiu, no una subvencio per hectarea real.
-- S'alineen exercici FEGA i campanya SIGPAC (mateix any) per comparabilitat.
--
-- Base: la superficie agraria per municipi (SIGPAC). Els municipis amb superficie pero
-- sense ajuda juridica registrada mostren import 0 (left join), no desapareixen.
{{ config(materialized="table") }}

with superficie as (
    select
        codi_ine,
        any_value(municipi) as municipi,
        any_value(comarca) as comarca,
        any_value(provincia) as provincia,
        round(sum(case when es_agrari then superficie_ha else 0 end), 2) as superficie_agraria_ha,
        any_value(exercici) as exercici
    from {{ ref("mart_superficie_cultiu_municipi") }}
    group by codi_ine
),

ajudes as (
    select
        codi_ine,
        sum(import_eur) as import_pac_juridiques_eur,
        count(distinct nom_beneficiari) as nombre_beneficiaris_juridics
    from {{ ref("mart_ajudes_pac_juridiques") }}
    where codi_ine is not null
      and exercici = {{ var("sigpac_campaign", 2025) }}
    group by codi_ine
)

select
    s.codi_ine,
    s.municipi,
    s.comarca,
    s.provincia,
    s.superficie_agraria_ha,
    coalesce(a.import_pac_juridiques_eur, 0) as import_pac_juridiques_eur,
    coalesce(a.nombre_beneficiaris_juridics, 0) as nombre_beneficiaris_juridics,
    case
        when s.superficie_agraria_ha > 0
        then round(coalesce(a.import_pac_juridiques_eur, 0) / s.superficie_agraria_ha, 2)
    end as import_eur_per_ha,
    s.exercici
from superficie s
left join ajudes a on a.codi_ine = s.codi_ine
