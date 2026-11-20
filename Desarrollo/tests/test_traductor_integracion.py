import os
from pathlib import Path

import pytest

import config
from modules.traductor import Traductor

RUTA_COMPROBANTE = Path(
    os.getenv(
        "TEST_RECEIPT_PATH",
        Path(__file__).resolve().parent / "fixtures" / "comprobante.pdf",
    )
)

pytestmark = pytest.mark.skipif(
    not config.GEMINI_API_KEY or not RUTA_COMPROBANTE.exists(),
    reason=(
        "Requiere GEMINI_API_KEY y un comprobante real en "
        "TEST_RECEIPT_PATH o tests/fixtures/comprobante.pdf"
    ),
)


async def test_traduccion_de_comprobante_real():
    contenido = RUTA_COMPROBANTE.read_bytes()
    mime_type = (
        "application/pdf"
        if RUTA_COMPROBANTE.suffix.lower() == ".pdf"
        else "image/jpeg"
    )

    resultado = await Traductor().traducir_comprobante(contenido, mime_type)

    assert resultado.monto is not None
    assert resultado.fecha is not None
    assert resultado.balance in ("INGRESO", "EGRESO")
