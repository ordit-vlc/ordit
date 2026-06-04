"""Logica d'enllac FEGA <-> SAT (linkage/sat.py), sense dades reals (CI-safe).

Sintetic: munta `fega` i `sat_raw` en memoria i comprova match/possible/no-match amb el
nucli-SAT del nom i el municipi com a desambiguador.
"""

import duckdb

from linkage.sat import measure


def _con():
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    con.execute("""insert into fega values
        ('A','SAT 9999 EXEMPLE FICTICI','Exemple de Dalt',100),   -- match (nucli + municipi)
        ('B','SAT N 8888 ALTRE EXEMPLE','Lloc Diferent',50),      -- possible (municipi distint)
        ('C','SAT 7777 INEXISTENT','Lloc X',10)                   -- no-match
    """)
    con.execute("create table sat_raw(nom varchar, num_reg varchar, municipi varchar)")
    con.execute("""insert into sat_raw values
        ('EXEMPLE FICTICI','9999','EXEMPLE DE DALT'),
        ('ALTRE EXEMPLE','8888','UN ALTRE')
    """)
    return con


def test_match_possible_nomatch():
    rep = measure(_con())
    assert rep["n"] == 3
    assert rep["n_match"] == 1  # nucli-SAT + municipi
    assert rep["n_possible"] == 1  # nucli-SAT igual, municipi distint
    assert rep["n_nomatch"] == 1


def test_match_per_numero_de_registre():
    # Nom que no casa pel nucli pero si pel numero de registre -> possible.
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    con.execute("insert into fega values ('A','SAT 9999 NOM QUE NO CASA','Lloc',100)")
    con.execute("create table sat_raw(nom varchar, num_reg varchar, municipi varchar)")
    con.execute("insert into sat_raw values ('TOTALMENT DISTINT','9999','Altre')")
    rep = measure(con)
    assert rep["n_match"] == 0
    assert rep["n_possible"] == 1  # casa pel Nº REGISTRO 9999
