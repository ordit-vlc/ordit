-- Mart: concessions de subvencions de la BDNS a la Comunitat Valenciana, TOTS els
-- beneficiaris (mode privat, cap filtre per tipus d'entitat). Una fila per concessio.
-- Columnes en valencia ASCII: el renom de l'angles intern al valencia es fa ací.
--
-- El premi respecte a FEGA: cada concessio porta el NIF/CIF del beneficiari (nif_cif),
-- la clau forta que habilita el backbone d'entitat canonica per CIF (Fase 6). Vegeu
-- docs/sources/bdns.md.
--
-- import_eur es l'import concedit; ajuda_equivalent_eur es l'ajuda equivalent (difereix en
-- garanties i prestecs, on l'equivalent es el subsidi real). Es mantenen els dos.
{{ config(materialized="table") }}

select
    grant_code as codi_concessio,
    grant_date as data_concessio,
    exercici,
    nif_cif,
    nom_beneficiari,
    es_persona_juridica,
    instrument,
    import_eur,
    ajuda_equivalent_eur,
    convocatoria,
    nivell_administracio,
    administracio,
    organ_concedent
from (
    select
        grant_code,
        grant_date,
        financial_year as exercici,
        nif_cif,
        beneficiary_name as nom_beneficiari,
        is_legal_person as es_persona_juridica,
        instrument,
        amount_eur as import_eur,
        equivalent_aid_eur as ajuda_equivalent_eur,
        call_title as convocatoria,
        admin_level1 as nivell_administracio,
        admin_level2 as administracio,
        admin_level3 as organ_concedent
    from {{ ref("staging_bdns") }}
)
