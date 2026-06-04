"""Logica d'enllac FEGA <-> SAT (linkage/sat.py), sense dades reals (CI-safe).

Nova logica d'estat -> match = numero de registre coincident (clau unica); possible = nucli
del nom (aproximat), sense numero coincident.
"""

import duckdb

from linkage.sat import measure


def _con():
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    con.execute("""insert into fega values
        ('A','SAT 9999 EXEMPLE FICTICI','Exemple de Dalt',100),  -- match (numero 9999 coincident)
        ('B','SAT N 8888 ALTRE EXEMPLE','Lloc',50),              -- possible (nucli; numero no casa)
        ('C','SAT 7777 INEXISTENT','Lloc X',10)                  -- no-match
    """)
    con.execute("create table sat_raw(nom varchar, num_reg varchar, municipi varchar)")
    con.execute("""insert into sat_raw values
        ('EXEMPLE FICTICI','9999','EXEMPLE DE DALT'),
        ('ALTRE EXEMPLE','5555','UN ALTRE')
    """)
    return con


def test_estat_nova_logica():
    rep = measure(_con())
    assert rep["n"] == 3
    assert rep["n_match"] == 1  # numero de registre coincident (9999)
    assert rep["n_possible"] == 1  # nucli del nom casa pero el numero no (8888 != 5555)
    assert rep["n_nomatch"] == 1


def test_match_per_numero_de_registre():
    # Nom que no casa pel nucli pero si pel numero de registre -> ara MATCH (clau unica).
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    con.execute("insert into fega values ('A','SAT 9999 NOM QUE NO CASA','Lloc',100)")
    con.execute("create table sat_raw(nom varchar, num_reg varchar, municipi varchar)")
    con.execute("insert into sat_raw values ('TOTALMENT DISTINT','9999','Altre')")
    rep = measure(con)
    assert rep["n_match"] == 1
    assert rep["n_possible"] == 0
