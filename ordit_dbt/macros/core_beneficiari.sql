{% macro core_beneficiari(col) %}
{#-
  Nucli del nom: clau canonica SENSE les paraules de forma juridica, per a pontejar variants
  d'abreviatura (p. ex. "SL" vs "SOCIEDAD LIMITADA", "COOP V" vs "S COOP V"). S'usa per a
  l'estat "possible" de l'enllac quan la clau canonica exacta no casa. Replica core() de
  linkage/coverage.py (mateixa definicio als dos costats).

  Passos: majuscules + plega accents -> puntuacio a espai -> lleva els tokens de forma
  juridica (dues passades, per a formes consecutives com "SOCIEDAD LIMITADA") -> lleva
  espais. Es nomes per a l'enllac, no s'exposa al mart.
-#}
{%- set legal = "SL|SA|SLU|SAU|SLL|SLP|SAL|SCV|SCA|SCCL|SC|SCP|CB|SAT|COOP|COOPERATIVA|SDAD|SOCIEDAD|LIMITADA|ANONIMA|CIVIL|AGRARIA|TRANSFORMACION|VALENCIANA|CV" -%}
{%- set spaced -%}
regexp_replace(' ' || upper(strip_accents({{ col }})) || ' ', '[^A-Z0-9]', ' ', 'g')
{%- endset -%}
{%- set no_legal = "regexp_replace(" ~ spaced ~ ", ' (" ~ legal ~ ") ', ' ', 'g')" -%}
{%- set no_legal2 = "regexp_replace(" ~ no_legal ~ ", ' (" ~ legal ~ ") ', ' ', 'g')" -%}
nullif(regexp_replace({{ no_legal2 }}, '[^A-Z0-9]', '', 'g'), '')
{% endmacro %}
