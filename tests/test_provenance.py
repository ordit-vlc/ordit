"""Guard de procedencia: cada contracte de font ha de portar la seua documentacio.

La procedencia es obligatoria (CLAUDE.md §5 i §8): cap fet sense una font traçable. Este
guard afirma que cada modul de contracte a contracts/ te el
seu docs/sources/<fil>.md amb les capçaleres requerides, perque no es puga afegir una font
sense documentar-la.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = ROOT / "contracts"
SOURCES_DIR = ROOT / "docs" / "sources"

# Capçaleres/tokens requerits a cada docs/sources/<fil>.md (cerca insensible a majuscules).
REQUIRED_TOKENS = (
    "procedència",
    "url",
    "llicència",
    "cadència",
    "data de descàrrega",
    "esquema",
    "peculiaritats",
)


def _contract_stems() -> list[str]:
    return sorted(p.stem for p in CONTRACTS_DIR.glob("*.py") if p.stem != "__init__")


CONTRACT_STEMS = _contract_stems()


def test_hi_ha_contractes_a_validar():
    assert CONTRACT_STEMS, "no s'ha trobat cap contracte a contracts/"


@pytest.mark.parametrize("stem", CONTRACT_STEMS)
def test_cada_contracte_te_doc_de_font(stem: str):
    doc = SOURCES_DIR / f"{stem}.md"
    assert doc.exists(), f"falta la documentacio de procedencia: docs/sources/{stem}.md"
    text = doc.read_text(encoding="utf-8").lower()
    missing = [tok for tok in REQUIRED_TOKENS if tok not in text]
    assert not missing, f"docs/sources/{stem}.md no conté: {missing}"
