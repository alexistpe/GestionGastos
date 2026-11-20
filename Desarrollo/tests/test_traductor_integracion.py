import os
from pathlib import Path

import pytest

import config
from modules.traductor import Traductor

DIRECTORIO_FIXTURES = Path(__file__).resolve().parent / "fixtures"

MIME_POR_EXTENSION = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _rutas_de_prueba() -> list[Path]:
    ruta_env = os.getenv("TEST_RECEIPT_PATH")
    if ruta_env:
        ruta = Path(ruta_env)
        return [ruta] if ruta.exists() else []

    if not DIRECTORIO_FIXTURES.exists():
        return []

    return sorted(
        ruta
        for ruta in DIRECTORIO_FIXTURES.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in MIME_POR_EXTENSION
    )


RUTAS = _rutas_de_prueba()
EJECUTAR_INTEGRACION = os.getenv("RUN_GEMINI_INTEGRATION") == "1"

pytestmark = pytest.mark.skipif(
    not EJECUTAR_INTEGRACION or not config.GEMINI_API_KEY or not RUTAS,
    reason=(
        "Requiere RUN_GEMINI_INTEGRATION=1, GEMINI_API_KEY y al menos un "
        "comprobante en TEST_RECEIPT_PATH o tests/fixtures/"
    ),
)


@pytest.mark.parametrize("ruta", RUTAS, ids=lambda ruta: ruta.name)
async def test_traduccion_de_comprobante_real(ruta):
    contenido = ruta.read_bytes()
    mime_type = MIME_POR_EXTENSION[ruta.suffix.lower()]

    resultado = await Traductor().traducir_comprobante(contenido, mime_type)

    assert resultado.monto is not None, resultado.advertencias
    assert resultado.fecha is not None, resultado.advertencias
    assert resultado.balance in ("INGRESO", "EGRESO"), resultado.advertencias
