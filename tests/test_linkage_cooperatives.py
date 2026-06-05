"""Logica d'enllac FEGA <-> cooperatives (linkage/cooperatives.py), sense dades reals.

Sintetic (CI-safe): un candidat UNIC es la mateixa entitat -> confirmat = n_candidats = 1
(siga exacte o nucli aproximat); ambigu = n_candidats > 1 (un nom amb >1 entitat).
"""

import duckdb

from linkage.cooperatives import measure


def _con():
    con = duckdb.connect()
    con.execute(
        "create table fega(clau varchar, nom_canonic varchar, municipi varchar, import_eur double)"
    )
    # confirmat: exacte+unic (EXEMPLE); confirmat tot i municipi distint (MAS FICTICI);
    # confirmat tot i duplicat de font amb mateix CIF (DUPLICADA, 2 files F005); ambigu: 2 CIF
    # distints comparteixen el nom (AMBIG); no-match (TERCERA).
    con.execute("""insert into fega values
        ('COOPERATIVAEXEMPLECOOPV','COOPERATIVA EXEMPLE COOP. V.','Exemple de Dalt',100),
        ('MASFICTICICOOPV','MAS FICTICI COOP V','Altre Lloc',50),
        ('DUPLICADACOOPV','DUPLICADA COOP V','Lloc D',70),
        ('AMBIGCOOPV','AMBIG COOP V','Lloc',80),
        ('TERCERACOOPV','TERCERA COOP V','Lloc X',10)
    """)
    con.execute(
        "create table coop_raw(nom varchar, cif varchar, clau_reg varchar, municipi varchar)"
    )
    # DUPLICADA: dues files, MATEIX CIF F005 (la mateixa coop duplicada) -> 1 candidat -> match.
    # AMBIG: dues files amb CIF DISTINTS (F003, F004) -> 2 candidats -> possible.
    con.execute("""insert into coop_raw values
        ('COOPERATIVA EXEMPLE COOP. V.','F001','V-1','EXEMPLE DE DALT'),
        ('MAS FICTICI COOP V','F002','V-2','UN ALTRE MUNICIPI'),
        ('DUPLICADA COOP. V.','F005','V-5','LLOC D'),
        ('DUPLICADA, COOP. V.','F005','V-5B','LLOC D'),
        ('AMBIG COOP V','F003','V-3','LLOC A'),
        ('AMBIG, COOP. V.','F004','V-4','LLOC B')
    """)
    return con


def test_estat_nova_logica():
    rep = measure(_con())
    assert rep["n"] == 5
    # confirmat = candidat unic: exacte+unic, municipi distint, i duplicat de font (mateix CIF).
    assert rep["n_confirmat"] == 3
    assert rep["n_ambigu"] == 1  # AMBIG: nom canonic casa amb 2 CIF distints (n_candidats > 1)
    assert rep["n_nomatch"] == 1


def test_duplicat_de_font_per_cif():
    # Una coop DUPLICADA al directori (mateix CIF, puntuacio distinta) NO es ambigua -> confirmat.
    rep = measure(_con())
    assert rep["ambig_n"] == 1  # nomes AMBIG (2 CIF distints), no el duplicat de mateix CIF


def test_cif_guanyat():
    rep = measure(_con())
    # confirmat (3) + ambigu (1) arrosseguen el CIF de la cooperativa.
    assert rep["n_cif"] == 4
