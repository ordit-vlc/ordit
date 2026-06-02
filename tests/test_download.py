"""Proves de l'extractor de FEGA. Tota la xarxa esta mockejada: cap crida real.

Cobreix la baixada (mockejada), la descompressio i la normalitzacio d'encoding
CP1252 -> UTF-8, mes la idempotencia.
"""

import io
import zipfile
from pathlib import Path

import pytest

from ingest.fega import download as dl

# Contingut de mostra amb un byte CP1252 cru (0x91 = cometa tipografica esquerra) per
# provar la normalitzacio. NOMES entitats ficticies.
_TXT_NAME = "Beneficiarios_municipio_ejercicio_financiero_2024.txt"
_SAMPLE_BYTES = b"BENEFICIARIO;IMPORTE_EUROS\r\nCOOP L\x91EXEMPLE;1.234,56\r\n"


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
    # El byte CP1252 0x91 s'ha de decodificar com a U+2018 (cometa esquerra), no trencar.
    assert "COOP L‘EXEMPLE" in text
    assert (tmp_path / _TXT_NAME).exists()  # el .txt original es conserva


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
