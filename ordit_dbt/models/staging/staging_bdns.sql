-- Staging de BDNS: neteja i tipa les concessions de subvencions (JSONL del raw) i en separa
-- el NIF/CIF incrustat al camp `beneficiario`. Capa interna: NO es publica i ho porta tot
-- (mode privat, cap filtre per tipus d'entitat). El filtre territorial (Comunitat Valenciana)
-- ja s'aplica en origen a la descarrega (regiones=54), no ací.
--
-- Peculiaritats de la font que es gestionen ací (vegeu docs/sources/bdns.md):
--   - `beneficiario` = "<NIF/CIF> <NOM>": el primer token de 9 alfanumerics es la clau forta
--     (FEGA no en porta); la resta es el nom. Codis ZZ...Z = entitats sense NIF estandard.
--   - lletra inicial del CIF A-W (excepte I/K/L/M/O/T) -> persona juridica o ens public.
--   - artefacte `*` al nom (no afecta el NIF/CIF): es neteja del nom.
--   - l'exercici no ve com a camp: s'extrau de l'any de fechaConcesion.
--
-- El glob es configurable via var per a validar amb fixtures sintetiques a CI (cap dada
-- real entra mai a git ni a CI).
{{ config(materialized="view") }}

with source as (
    select *
    from read_json(
        '{{ var("bdns_raw_glob", "../data/raw/bdns/concesiones_cv_*.jsonl") }}',
        format = 'newline_delimited',
        columns = {
            'id': 'BIGINT', 'codConcesion': 'VARCHAR', 'fechaConcesion': 'DATE',
            'beneficiario': 'VARCHAR', 'instrumento': 'VARCHAR', 'importe': 'DOUBLE',
            'ayudaEquivalente': 'DOUBLE', 'urlBR': 'VARCHAR', 'tieneProyecto': 'BOOLEAN',
            'numeroConvocatoria': 'VARCHAR', 'idConvocatoria': 'BIGINT',
            'convocatoria': 'VARCHAR', 'descripcionCooficial': 'VARCHAR',
            'nivel1': 'VARCHAR', 'nivel2': 'VARCHAR', 'nivel3': 'VARCHAR',
            'codigoInvente': 'VARCHAR', 'idPersona': 'BIGINT', 'fechaAlta': 'DATE'
        }
    )
),

parsed as (
    select
        id as grant_id,
        codConcesion as grant_code,
        fechaConcesion as grant_date,
        beneficiario as beneficiary_raw,
        -- NIF/CIF: primer token de 9 alfanumerics; '' si no casa (mai observat al real).
        nullif(regexp_extract(beneficiario, '^([0-9A-Z]{9})\s', 1), '') as nif_cif,
        -- Nom sense el NIF/CIF inicial i sense l'artefacte `*` final.
        trim(regexp_replace(
            regexp_replace(beneficiario, '^[0-9A-Z]{9}\s+', ''),
            '\s*\*\s*$', ''
        )) as beneficiary_name,
        instrumento as instrument,
        importe as amount_eur,
        ayudaEquivalente as equivalent_aid_eur,
        urlBR as url_br,
        tieneProyecto as has_project,
        numeroConvocatoria as call_number,
        idConvocatoria as call_id,
        convocatoria as call_title,
        descripcionCooficial as call_title_cooficial,
        nivel1 as admin_level1,
        nivel2 as admin_level2,
        nivel3 as admin_level3,
        idPersona as person_id,
        year(fechaConcesion) as financial_year
    from source
)

select
    *,
    -- Persona juridica / ens public: lletra inicial del CIF a A-W (exclou I/K/L/M/O/T,
    -- DNI de fisica i codis ZZ). Es la clau forta utilitzable per al backbone (Fase 6).
    (nif_cif is not null and left(nif_cif, 1) in (
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'N', 'P', 'Q', 'R', 'S', 'U', 'V', 'W'
    )) as is_legal_person
from parsed
