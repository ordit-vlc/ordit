"""Logica de mesura de l'spike FEGA x BORME (linkage/coverage.py), sense dades reals.

Sintetic (CI-safe): munta fega/borme en memoria amb DuckDB i comprova la classificacio
match / possible / no-match i la deteccio d'ambiguitat.
"""

import duckdb

from linkage.coverage import measure


def _con():
    con = duckdb.connect()
    con.execute("create table fega(nom varchar, import_eur double)")
    con.execute("""insert into fega values
        ('GREENMED SL', 100),               -- match exacte
        ('HORT EXEMPLE SL', 50),            -- possible (nucli, vs 'SOCIEDAD LIMITADA')
        ('MAS INEXISTENT SL', 10),          -- no-match
        ('AMBIG SL', 80)                    -- match pero ambigu (2 variants a BORME)
    """)
    con.execute("create table borme(nom varchar)")
    con.execute("""insert into borme values
        ('GREENMED SL'),
        ('HORT EXEMPLE SOCIEDAD LIMITADA'),
        ('AMBIG SL'),
        ('AMBIG, S.L.')
    """)
    return con


def test_classificacio_i_cobertura():
    rep = measure(_con())
    j = rep["juridic"]
    assert j["n"] == 4
    assert j["n_match"] == 2  # GREENMED, AMBIG
    assert j["n_possible"] == 1  # HORT EXEMPLE (nucli)
    assert j["n_nomatch"] == 1  # MAS INEXISTENT
    # Tots son SL -> mercantil = juridic.
    assert rep["mercantil"]["n"] == 4


def test_ambiguitat():
    rep = measure(_con())
    # 3 matchejats (match+possible); 1 ambigu (AMBIG casa amb 2 empreses BORME).
    assert rep["ambig_total"] == 3
    assert rep["ambig_n"] == 1
    assert any("AMBIG" in row[0] for row in rep["ambig_examples"])
