{% macro canon_beneficiari(col) %}
{#-
  Clau canonica de beneficiari: normalitzacio simple i agressiva, font unica. FEGA no porta
  CIF, aixi que la identitat depen del nom. La clau plega variants de la MATEIXA entitat
  (espais, puntuacio, accents i formes juridiques per espaiat/punts) sense fusionar-ne de
  distintes.

  Regla (una sola passada): plega accents (strip_accents) + majuscules + elimina TOT allo que
  NO siga alfanumeric (espais i puntuacio inclosos). Sense llista de formes juridiques:
  eliminar espais i puntuacio ja unifica per si sol
    "GREENMED SL" / "GREENMED S.L." / "GREENMED S. L."        -> "GREENMEDSL"
    "GREEN FRUITS COOP. V." / "GREENFRUITS COOP. V."          -> "GREENFRUITSCOOPV"

  Precision-first PER CONSTRUCCIO: la clau nomes col.lapsa si la seqüencia de lletres i xifres
  coincideix; "FOO SL" != "FOO SA" i "FOO" != "FOO SL".

  Limitacio: NO unifica equivalencies d'abreviatura amb lletres distintes (p. ex. "S COOP V"
  vs "SCV", o "NUMERO" vs "N"). Es el preu de simplificar; vegeu docs/sources/fega.md.
-#}
nullif(regexp_replace(upper(strip_accents({{ col }})), '[^A-Z0-9]', '', 'g'), '')
{% endmacro %}
