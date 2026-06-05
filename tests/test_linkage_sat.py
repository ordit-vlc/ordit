"""Logica d'enllac FEGA <-> SAT (linkage/sat.py), sense dades reals (CI-safe).

Un candidat UNIC es la mateixa entitat -> confirmat = n_candidats = 1 (per codi o per nucli);
ambigu = n_candidats > 1. El nucli numeric pot conflar dos registres (nacional "55" vs
autonomic "55CV"): el NOM desambigua si nomes una entrada hi casa.
"""

import duckdb

from linkage.sat import measure


def _con():
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    # A: confirmat (codi 9999 unic). D: confirmat (codi, directori amb sufix 7777CV).
    # F: codi 55 conflà dos registres (55 i 55CV) pero el NOM (BONA EMPRESA) desambigua ->
    # confirmat. G: codi 88 conflà dos registres i el nom NO casa cap -> ambigu. C: no-match.
    con.execute("""insert into fega values
        ('A','SAT 9999 EXEMPLE FICTICI','Dalt',100),
        ('D','SAT 7777 SUFIX EXEMPLE','Lloc D',70),
        ('F','SAT 55CV BONA EMPRESA','Lloc F',60),
        ('G','SAT 88 NOM DESCONEGUT','Lloc G',40),
        ('C','SAT 6666 INEXISTENT','Lloc X',10)
    """)
    con.execute("create table sat_raw(nom varchar, num_reg varchar, municipi varchar)")
    con.execute("""insert into sat_raw values
        ('EXEMPLE FICTICI','9999','DALT'),
        ('SUFIX EXEMPLE','7777CV','LLOC D'),
        ('ALTRA COSA','55','UN LLOC'),
        ('BONA EMPRESA','55CV','LLOC F'),
        ('PRIMERA','88','UN LLOC'),
        ('SEGONA','88CV','ALTRE LLOC')
    """)
    return con


def test_estat_nova_logica():
    rep = measure(_con())
    assert rep["n"] == 5
    # confirmat: codi unic (9999), codi+sufix (7777CV), i codi-conflat resolt pel nom (55CV).
    assert rep["n_confirmat"] == 3
    assert rep["n_ambigu"] == 1  # codi 88 conflà dos registres i el nom no desambigua
    assert rep["n_nomatch"] == 1


def test_confirmat_pel_numero_amb_sufix_cv():
    # El directori porta el numero amb sufix d'ambit ("9999CV"); FEGA encasta nomes "9999".
    # El nucli numeric ha de casar -> CONFIRMAT (codi unic), encara que el nom no casa gens.
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    con.execute("insert into fega values ('A','SAT 9999 NOM QUE NO CASA','Lloc',100)")
    con.execute("create table sat_raw(nom varchar, num_reg varchar, municipi varchar)")
    con.execute("insert into sat_raw values ('TOTALMENT DISTINT','9999CV','Altre')")
    rep = measure(con)
    assert rep["n_confirmat"] == 1
    assert rep["n_ambigu"] == 0
