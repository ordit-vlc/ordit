"""Logica d'enllac FEGA <-> cooperatives (linkage/cooperatives.py), sense dades reals.

Sintetic (CI-safe): munta `fega` i `coop_raw` en memoria i comprova match/possible/no-match,
el municipi com a desambiguador i el CIF arrossegat.
"""

import duckdb

from linkage.cooperatives import measure


def _con():
    con = duckdb.connect()
    # `fega`: una fila per (clau canonica, municipi). clau = canon del nom.
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    con.execute("""insert into fega values
        ('COOPERATIVAEXEMPLECOOPV','COOPERATIVA EXEMPLE COOP. V.','Exemple de Dalt',100),
        ('MASFICTICICOOPV','MAS FICTICI COOP V','Altre Lloc',50),
        ('TERCERACOOPV','TERCERA COOP V','Lloc X',10)
    """)
    # `coop_raw`: directori (nom, cif, clau_reg, municipi).
    con.execute(
        "create table coop_raw(nom varchar, cif varchar, clau_reg varchar, municipi varchar)"
    )
    con.execute("""insert into coop_raw values
        ('COOPERATIVA EXEMPLE COOP. V.','F001','V-1','EXEMPLE DE DALT'),
        ('MAS FICTICI COOP V','F002','V-2','UN ALTRE MUNICIPI')
    """)
    return con


def test_match_possible_nomatch():
    rep = measure(_con())
    assert rep["n"] == 3
    assert rep["n_match"] == 1  # canon + municipi coincident
    assert rep["n_possible"] == 1  # canon igual, municipi distint
    assert rep["n_nomatch"] == 1  # sense cooperativa al directori


def test_cif_guanyat():
    rep = measure(_con())
    # Les 2 entitats matchejades (match+possible) arrosseguen el CIF de la cooperativa.
    assert rep["n_cif"] == 2
