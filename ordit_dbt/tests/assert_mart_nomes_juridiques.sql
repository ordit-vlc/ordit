-- Gate RGPD (#5): el mart de juridiques no pot contindre cap persona fisica.
-- Cap fila ES#... i cap beneficiari que no estiga classificat 'legal' a l'intermediate.
-- El test passa si no torna cap fila.
select m.nom_beneficiari, m.municipi, m.exercici
from {{ ref("mart_ajudes_pac_juridiques") }} m
where m.nom_beneficiari like 'ES#%'
    or not exists (
        select 1
        from {{ ref("int_fega_classified") }} i
        where i.beneficiary_name = m.nom_beneficiari
            and i.entity_type = 'legal'
    )
