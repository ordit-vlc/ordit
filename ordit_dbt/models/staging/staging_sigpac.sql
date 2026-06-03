-- Staging de SIGPAC: llig el CSV agregat de recintes (superficie per municipi-catastro,
-- us i grup de cultiu) que produeix ingest/sigpac/aggregate.py. Capa interna (anglés
-- ASCII): NO es publica. Aci nomes es tipa i es neteja; la resolucio catastro -> codi_ine
-- i el renom a valencia es fan aigües avall (intermediate i marts).
--
-- Per que un CSV agregat i no el SHP cru? Els recintes son milions de poligons (ROADMAP
-- No-go de la Fase 2: massa per a la memoria del build plane). La ingestio els agrega
-- atribut-only (sense geometria) a milers de files; dbt consumeix eixe agregat. Vegeu
-- docs/sources/sigpac.md.
--
-- El path es configurable via var per a validar amb una fixture sintetica a CI (cap
-- descarrega de ~1,3 GB ni cap geometria entra mai a git ni a CI).
{{ config(materialized="view") }}

select
    catastro_code,                       -- codi de municipi de catastro: provincia(2)+municipi(3)
    upper(trim(uso_sigpac)) as land_use,  -- codi d'us SIGPAC (llista tancada de 2 lletres)
    nullif(upper(trim(grupo_cult)), '') as crop_group,  -- TCR/TCS/CP/PP o NULL
    n_recintes::bigint as n_recintes,
    surface_m2::decimal(18, 2) as surface_m2,
    {{ var("sigpac_campaign", 2025) }}::int as campaign  -- campanya SIGPAC (del nom de fitxer)
from read_csv(
    '{{ var("sigpac_agg_path", "../data/raw/sigpac/recintos_agg_2025.csv") }}',
    header = true,
    columns = {
        'catastro_code': 'VARCHAR', 'uso_sigpac': 'VARCHAR', 'grupo_cult': 'VARCHAR',
        'n_recintes': 'BIGINT', 'surface_m2': 'DOUBLE'
    }
)
