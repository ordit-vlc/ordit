"""Proves de l'extractor de FEGA. Tota la xarxa esta mockejada: cap crida real.

Cobreix la baixada (mockejada), la descompressio i la normalitzacio d'encoding mixt
(latin-1 + UTF-8 mal interpretat + especials CP1252), mes la idempotencia.
"""

import io
import zipfile
from pathlib import Path

import pytest

from ingest.fega import download as dl

# Mostra amb els tres casos d'encoding mixt del fitxer real de FEGA (NOMES ficticis):
#   - "I" amb accent agut ja en UTF-8: bytes 0xC3 0x8D (el cas conegut "AGRICOLA").
#   - "a" amb accent greu en latin-1: byte 0xE0.
#   - cometa tipografica de CP1252: byte 0x91.
_TXT_NAME = "Beneficiarios_municipio_ejercicio_financiero_2024.txt"
_SAMPLE_BYTES = (
    b"BENEFICIARIO;MUNICIPIO;IMPORTE_EUROS\r\n"
    b"COOP VALENCIANA AGR\xc3\x8dCOLA DEL BAJO TURIA;46165 - Bugarra;1.234,56\r\n"
    b"COOP L\x91EXEMPLE D'ALM\xe0SSERA;46000 - Test;2,00\r\n"
)


def _fake_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(_TXT_NAME, _SAMPLE_BYTES)
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._data


@pytest.fixture
def no_network(monkeypatch):
    zip_bytes = _fake_zip_bytes()

    def fake_urlopen(req, timeout=0):
        return _FakeResponse(zip_bytes)

    monkeypatch.setattr(dl.urllib.request, "urlopen", fake_urlopen)


def test_download_one_baixa_descomprimeix_i_normalitza(no_network, tmp_path: Path):
    url = "https://example.test/datos-2024.zip"
    utf8 = dl._download_one(2024, url, tmp_path)

    assert utf8.name.endswith(".utf8.txt")
    text = utf8.read_text(encoding="utf-8")
    # El cas conegut: l'UTF-8 mal interpretat es repara (no "AGRÃ�COLA").
    assert "AGRÍCOLA DEL BAJO TURIA" in text
    # latin-1 i cometa CP1252 alhora, sense trencar.
    assert "COOP L‘EXEMPLE D'ALMàSSERA" in text
    assert (tmp_path / _TXT_NAME).exists()  # el .txt original es conserva


def test_decode_mixed_repara_encoding_mixt():
    # UTF-8 (0xC3 0x8D = Í) + latin-1 (0xE0 = à) + CP1252 (0x91 = ‘) en una sola cadena.
    raw = b"AGR\xc3\x8dCOLA;Alm\xe0ssera;L\x91Olleria"
    assert dl.decode_mixed(raw) == "AGRÍCOLA;Almàssera;L‘Olleria"


def test_download_one_es_idempotent(no_network, tmp_path: Path):
    url = "https://example.test/datos-2024.zip"
    first = dl._download_one(2024, url, tmp_path)
    mtime = first.stat().st_mtime_ns
    # Segona passada: no ha de tornar a baixar ni reescriure.
    again = dl._download_one(2024, url, tmp_path)
    assert again == first
    assert again.stat().st_mtime_ns == mtime


def test_download_itera_tots_els_exercicis(monkeypatch, tmp_path: Path):
    seen = []

    def fake_one(year, url, dest):
        seen.append(year)
        return dest / f"{year}.utf8.txt"

    monkeypatch.setattr(dl, "_download_one", fake_one)
    out = dl.download(dest_dir=tmp_path)
    assert seen == sorted(dl.EXERCISES)
    assert len(out) == len(dl.EXERCISES)
