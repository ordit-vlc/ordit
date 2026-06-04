"""Logica d'enllac FEGA <-> cooperatives (linkage/cooperatives.py), sense dades reals.

Sintetic (CI-safe): nova logica d'estat -> match = nom canonic EXACTE i candidat UNIC (siga
quin siga el municipi); possible = nucli (aproximat) o exacte ambigu (>1 cooperativa).
"""

import duckdb

from linkage.cooperatives import measure


def _con():
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    # match: exacte+unic (EXEMPLE); match tot i municipi distint (MAS FICTICI); possible:
    # exacte ambigu, 2 cooperatives (AMBIG); no-match (TERCERA).
    con.execute("""insert into fega values
        ('COOPERATIVAEXEMPLECOOPV','COOPERATIVA EXEMPLE COOP. V.','Exemple de Dalt',100),
        ('MASFICTICICOOPV','MAS FICTICI COOP V','Altre Lloc',50),
        ('AMBIGCOOPV','AMBIG COOP V','Lloc',80),
        ('TERCERACOOPV','TERCERA COOP V','Lloc X',10)
    """)
    con.execute(
        "create table coop_raw(nom varchar, cif varchar, clau_reg varchar, municipi varchar)"
    )
    con.execute("""insert into coop_raw values
        ('COOPERATIVA EXEMPLE COOP. V.','F001','V-1','EXEMPLE DE DALT'),
        ('MAS FICTICI COOP V','F002','V-2','UN ALTRE MUNICIPI'),
        ('AMBIG COOP V','F003','V-3','LLOC A'),
        ('AMBIG, COOP. V.','F004','V-4','LLOC B')
    """)
    return con


def test_estat_nova_logica():
    rep = measure(_con())
    assert rep["n"] == 4
    assert rep["n_match"] == 2  # exacte + unic, encara que el municipi diferisca
    assert rep["n_possible"] == 1  # AMBIG: nom canonic casa amb 2 cooperatives
    assert rep["n_nomatch"] == 1


def test_cif_guanyat():
    rep = measure(_con())
    # match (2) + possible (1) arrosseguen el CIF de la cooperativa.
    assert rep["n_cif"] == 3
