{% macro sat_namekey(col) %}
{#-
  Clau de nom robusta per a SAT: com sat_core (lleva els tokens de forma/registre SAT/NUM/N/CV
  i els numeros), pero a mes parteix en paraules, les ORDENA i les concatena. Aixi neutralitza
  la inversio d'article i l'ordre de paraules: "LA SOLANA" i "SOLANA, LA" donen la mateixa clau
  ("LASOLANA"). Replica sat_namekey() de linkage/sat.py. Dues passades per als tokens consecutius.
-#}
{%- set toks = "SAT|NUM|N|CV|SDAD|SOCIEDAD|AGRARIA|TRANSFORMACION|LTDA|LIMITADA" -%}
{%- set base -%}
regexp_replace(' ' || upper(strip_accents({{ col }})) || ' ', '[^A-Z0-9]', ' ', 'g')
{%- endset -%}
{%- set s1 = "regexp_replace(" ~ base ~ ", ' (" ~ toks ~ ") ', ' ', 'g')" -%}
{%- set s2 = "regexp_replace(" ~ s1 ~ ", ' (" ~ toks ~ ") ', ' ', 'g')" -%}
{#- lleva qualsevol token que comence per digit: numeros purs ("498") i numero+ambit ("265CV"). -#}
{%- set s3 = "regexp_replace(" ~ s2 ~ ", ' [0-9][A-Z0-9]* ', ' ', 'g')" -%}
nullif(
    array_to_string(
        list_sort(
            list_filter(string_split_regex(trim({{ s3 }}), '[^A-Z0-9]+'), x -> length(x) >= 1)
        ),
        ''
    ),
    ''
)
{% endmacro %}
