import asyncio
import json

import pytest

from modules.gestion import Gestion
from modules.traductor import (
    ESQUEMA_RESPUESTA,
    ComprobanteExtraido,
    ErrorTraduccion,
    Traductor,
)


class _Respuesta:
    def __init__(self, text):
        self.text = text


class _Modelos:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    async def generate_content(self, **kwargs):
        self.llamadas.append(kwargs)
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, BaseException):
            raise respuesta
        return _Respuesta(respuesta)


class _Aio:
    def __init__(self, modelos):
        self.models = modelos


class _Cliente:
    def __init__(self, respuestas):
        self.aio = _Aio(_Modelos(respuestas))


def json_valido(**cambios):
    datos = {
        "fecha": "2026-11-15",
        "destino": "YPF",
        "monto": 15000,
        "balance": "EGRESO",
        "moneda": "ARS",
    }
    datos.update(cambios)
    return json.dumps(datos)


async def test_traduccion_valida():
    cliente = _Cliente([json_valido()])
    traductor = Traductor(cliente=cliente, modelo="gemini-prueba", timeout=1)

    resultado = await traductor.traducir_comprobante(
        b"imagen", "image/jpeg", contexto="nafta"
    )

    assert isinstance(resultado, ComprobanteExtraido)
    assert resultado.fecha == "2026-11-15"
    assert resultado.destino == "YPF"
    assert resultado.monto == 15000
    assert resultado.balance == "EGRESO"
    assert resultado.moneda == "ARS"
    assert resultado.advertencias == []
    assert resultado.a_dict()["monto"] == 15000

    assert len(cliente.aio.models.llamadas) == 1
    llamada = cliente.aio.models.llamadas[0]
    assert llamada["model"] == "gemini-prueba"
    assert llamada["config"].response_mime_type == "application/json"
    assert llamada["config"].response_schema == ESQUEMA_RESPUESTA
    assert "nafta" in llamada["contents"][1]


async def test_traduccion_con_campos_faltantes():
    texto = json.dumps(
        {
            "fecha": None,
            "destino": None,
            "monto": None,
            "balance": None,
            "moneda": None,
        }
    )
    traductor = Traductor(cliente=_Cliente([texto]))

    resultado = await traductor.traducir_comprobante(b"x", "image/png")

    assert resultado.fecha is None
    assert resultado.destino is None
    assert resultado.monto is None
    assert resultado.balance is None
    assert resultado.moneda == "ARS"
    assert len(resultado.advertencias) == 4


async def test_traduccion_normaliza_formatos():
    texto = json_valido(
        fecha="15.11.26",
        destino="  YPF  ",
        monto="$15.000,50",
        balance="egreso",
        moneda="ars",
    )
    traductor = Traductor(cliente=_Cliente([texto]))

    resultado = await traductor.traducir_comprobante(b"x", "image/jpeg")

    assert resultado.fecha == "2026-11-15"
    assert resultado.destino == "YPF"
    assert resultado.monto == pytest.approx(15000.5)
    assert resultado.balance == "EGRESO"
    assert resultado.moneda == "ARS"


async def test_traduccion_acepta_code_fences():
    texto = f"```json\n{json_valido()}\n```"
    traductor = Traductor(cliente=_Cliente([texto]))

    resultado = await traductor.traducir_comprobante(b"x", "application/pdf")

    assert resultado.monto == 15000


async def test_traduccion_respuesta_invalida():
    traductor = Traductor(cliente=_Cliente(["esto no es json"]))

    with pytest.raises(ErrorTraduccion):
        await traductor.traducir_comprobante(b"x", "image/png")


async def test_traduccion_respuesta_vacia():
    traductor = Traductor(cliente=_Cliente([""]))

    with pytest.raises(ErrorTraduccion):
        await traductor.traducir_comprobante(b"x", "image/png")


async def test_timeout_reintenta_una_vez():
    cliente = _Cliente([asyncio.TimeoutError(), json_valido()])
    traductor = Traductor(cliente=cliente, timeout=0.01)

    resultado = await traductor.traducir_comprobante(b"x", "image/png")

    assert resultado.monto == 15000
    assert len(cliente.aio.models.llamadas) == 2


async def test_timeout_dos_veces_falla():
    cliente = _Cliente([asyncio.TimeoutError(), asyncio.TimeoutError()])
    traductor = Traductor(cliente=cliente, timeout=0.01)

    with pytest.raises(ErrorTraduccion) as error:
        await traductor.traducir_comprobante(b"x", "image/png")

    assert "tardó" in str(error.value)
    assert len(cliente.aio.models.llamadas) == 2


async def test_error_inesperado_de_la_api():
    traductor = Traductor(cliente=_Cliente([RuntimeError("boom")]))

    with pytest.raises(ErrorTraduccion):
        await traductor.traducir_comprobante(b"x", "image/png")


async def test_mime_no_soportado():
    traductor = Traductor(cliente=_Cliente([]))

    with pytest.raises(ErrorTraduccion):
        await traductor.traducir_comprobante(b"x", "text/plain")


async def test_mime_jpg_se_normaliza():
    traductor = Traductor(cliente=_Cliente([json_valido()]))

    resultado = await traductor.traducir_comprobante(b"x", "image/jpg")

    assert resultado.monto == 15000


async def test_archivo_vacio():
    traductor = Traductor(cliente=_Cliente([]))

    with pytest.raises(ErrorTraduccion):
        await traductor.traducir_comprobante(b"", "image/png")


async def test_sin_api_key():
    traductor = Traductor(api_key="", cliente=None)

    with pytest.raises(ErrorTraduccion) as error:
        await traductor.traducir_comprobante(b"x", "image/png")

    assert "GEMINI_API_KEY" in str(error.value)


async def test_balance_invalido():
    texto = json_valido(balance="otro")
    traductor = Traductor(cliente=_Cliente([texto]))

    resultado = await traductor.traducir_comprobante(b"x", "image/png")

    assert resultado.balance is None
    assert "No se pudo determinar el balance." in resultado.advertencias


async def test_gestion_iniciar_traduccion(db_path):
    traductor = Traductor(cliente=_Cliente([json_valido()]), modelo="test")
    gestion = Gestion(db_path, traductor=traductor)

    assert gestion.conocer_traductor() is traductor

    resultado = await gestion.iniciar_traduccion(
        b"x", "image/png", contexto="gym"
    )

    assert resultado["monto"] == 15000
    assert resultado["balance"] == "EGRESO"
    assert resultado["advertencias"] == []
