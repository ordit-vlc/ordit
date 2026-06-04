{% macro sat_core(col) %}
{#-
  Nucli-SAT: nom sense els tokens de forma/registre (SAT/NUM/N/CV...) ni numeros. FEGA
  encasta "SAT <num>" al nom de forma inconsistent ("SAT 9912 CITRICOS", "SAT N 163 ALBA",
  "SAT NUM 8642 D,OR"), mentre que el directori de SAT porta la denominacio neta amb el
  Nº REGISTRO a banda. El nucli alinea els dos costats per a l'enllac. Replica sat_core() de
  linkage/sat.py. Dues passades per als tokens consecutius.
-#}
{%- set toks = "SAT|NUM|N|CV|SDAD|SOCIEDAD|AGRARIA|TRANSFORMACION|LTDA|LIMITADA" -%}
{%- set base -%}
regexp_replace(' ' || upper(strip_accents({{ col }})) || ' ', '[^A-Z0-9]', ' ', 'g')
{%- endset -%}
{%- set s1 = "regexp_replace(" ~ base ~ ", ' (" ~ toks ~ ") ', ' ', 'g')" -%}
{%- set s2 = "regexp_replace(" ~ s1 ~ ", ' (" ~ toks ~ ") ', ' ', 'g')" -%}
{%- set s3 = "regexp_replace(" ~ s2 ~ ", ' [0-9]+ ', ' ', 'g')" -%}
nullif(regexp_replace({{ s3 }}, '[^A-Z0-9]', '', 'g'), '')
{% endmacro %}
