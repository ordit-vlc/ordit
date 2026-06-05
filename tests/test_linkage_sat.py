"""Logica d'enllac FEGA <-> SAT (linkage/sat.py), sense dades reals (CI-safe).

Nom + municipi son l'autoritat; el numero nomes corrobora (pot estar mal escrit a FEGA). Es
puntua cada candidat (nom 4 + numero 2 + municipi 1): confirmat si nomes un empata al cim,
ambigu si >=2, no-match si cap. metode: codi / nom+municipi / rescat / nucli.
"""

import duckdb

from linkage.sat import build_classified, measure


def _con():
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    # A confirmat per codi+nom. B confirmat per nom+municipi amb INVERSIO D'ARTICLE i sense
    # numero (LA COSTERA = COSTERA, LA). C RESCAT: el numero (200) es erroni; nom+municipi
    # porten a 888CV. D ambigu: 88 conflà dos registres i ni nom ni municipi desambiguen. E
    # no-match.
    con.execute("""insert into fega values
        ('A','SAT 9999 EXEMPLE FICTICI','Dalt',100),
        ('B','SAT LA COSTERA','Xativa',80),
        ('C','SAT 200 MARCA NOVA','Vila-real',60),
        ('D','SAT 88 NOM X','Llocx',40),
        ('E','SAT 6666 RES','Llocz',10)
    """)
    con.execute("create table sat_raw(nom varchar, num_reg varchar, municipi varchar)")
    con.execute("""insert into sat_raw values
        ('EXEMPLE FICTICI','9999','Dalt'),
        ('COSTERA, LA','70','Xativa'),
        ('MARCA NOVA','888CV','Vila-real'),
        ('ALTRA EMPRESA','200','Castello'),
        ('PRIMERA','88','Un Lloc'),
        ('SEGONA','88CV','Altre Lloc')
    """)
    return con


def test_estat_nova_logica():
    rep = measure(_con())
    assert rep["n"] == 5
    assert rep["n_confirmat"] == 3  # codi (A), nom+municipi amb inversio d'article (B), rescat (C)
    assert rep["n_ambigu"] == 1  # 88 conflà dos registres i res no desambigua (D)
    assert rep["n_nomatch"] == 1  # E


def test_metode_rescat_i_nom_municipi():
    con = _con()
    build_classified(con)
    rows = dict(
        con.execute("select clau, metode || ':' || num_registre from classified").fetchall()
    )
    # C: el numero de FEGA (200) era erroni; nom+municipi rescaten el registre real 888CV.
    assert rows["C"] == "rescat:888CV"
    # B: inversio d'article resolta per la clau de tokens ordenats; sense numero -> nom+municipi.
    assert rows["B"] == "nom+municipi:70"
    assert rows["A"].startswith("codi:")
