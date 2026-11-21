import base64
import json

import httpx
import pytest

import config
from modules.gestion import Gestion
from modules.traductor import (
    ESQUEMA_RESPUESTA,
    INSTRUCCION_SISTEMA,
    ComprobanteExtraido,
    ErrorTraduccion,
    Traductor,
)

CLAVE = "clave-prueba"


def respuesta_ok(texto: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": texto}]}}]}


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


def cliente_con(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_traduccion_valida_y_request(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_VERSION", "v1beta")
    solicitudes = []

    async def handler(request: httpx.Request) -> httpx.Response:
        solicitudes.append(request)
        return httpx.Response(200, json=respuesta_ok(json_valido()))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(
            api_key=CLAVE,
            cliente_http=cliente,
            modelo="models/gemini-prueba",
            timeout=1,
        )
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

    assert len(solicitudes) == 1
    request = solicitudes[0]
    assert request.method == "POST"
    assert str(request.url) == (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-prueba:generateContent"
    )
    assert request.headers["x-goog-api-key"] == CLAVE

    payload = json.loads(request.content)
    assert payload["systemInstruction"]["parts"][0]["text"] == (
        INSTRUCCION_SISTEMA
    )
    partes = payload["contents"][0]["parts"]
    assert partes[0]["inlineData"]["mimeType"] == "image/jpeg"
    assert partes[0]["inlineData"]["data"] == base64.b64encode(
        b"imagen"
    ).decode("ascii")
    assert "nafta" in partes[1]["text"]
    configuracion = payload["generationConfig"]
    assert configuracion["temperature"] == 0
    assert configuracion["responseMimeType"] == "application/json"
    assert configuracion["responseSchema"] == ESQUEMA_RESPUESTA


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

    async def handler(request):
        return httpx.Response(200, json=respuesta_ok(texto))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
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

    async def handler(request):
        return httpx.Response(200, json=respuesta_ok(texto))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        resultado = await traductor.traducir_comprobante(b"x", "image/jpeg")

    assert resultado.fecha == "2026-11-15"
    assert resultado.destino == "YPF"
    assert resultado.monto == pytest.approx(15000.5)
    assert resultado.balance == "EGRESO"
    assert resultado.moneda == "ARS"


async def test_traduccion_acepta_code_fences():
    texto = f"```json\n{json_valido()}\n```"

    async def handler(request):
        return httpx.Response(200, json=respuesta_ok(texto))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        resultado = await traductor.traducir_comprobante(
            b"x", "application/pdf"
        )

    assert resultado.monto == 15000


async def test_traduccion_respuesta_invalida():
    async def handler(request):
        return httpx.Response(200, json=respuesta_ok("esto no es json"))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        with pytest.raises(ErrorTraduccion):
            await traductor.traducir_comprobante(b"x", "image/png")


async def test_traduccion_respuesta_vacia():
    async def handler(request):
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": ""}]}}]}
        )

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        with pytest.raises(ErrorTraduccion):
            await traductor.traducir_comprobante(b"x", "image/png")


async def test_traduccion_sin_candidatos():
    async def handler(request):
        return httpx.Response(200, json={})

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        with pytest.raises(ErrorTraduccion):
            await traductor.traducir_comprobante(b"x", "image/png")


async def test_traduccion_bloqueada():
    async def handler(request):
        return httpx.Response(
            200, json={"promptFeedback": {"blockReason": "SAFETY"}}
        )

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        with pytest.raises(ErrorTraduccion) as error:
            await traductor.traducir_comprobante(b"x", "image/png")

    assert "bloqueó" in str(error.value)


async def test_timeout_reintenta_una_vez():
    solicitudes = []

    async def handler(request):
        solicitudes.append(request)
        if len(solicitudes) == 1:
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(200, json=respuesta_ok(json_valido()))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(
            api_key=CLAVE, cliente_http=cliente, timeout=1
        )
        resultado = await traductor.traducir_comprobante(b"x", "image/png")

    assert resultado.monto == 15000
    assert len(solicitudes) == 2


async def test_timeout_dos_veces_falla():
    solicitudes = []

    async def handler(request):
        solicitudes.append(request)
        raise httpx.ReadTimeout("timeout", request=request)

    async with cliente_con(handler) as cliente:
        traductor = Traductor(
            api_key=CLAVE, cliente_http=cliente, timeout=1
        )
        with pytest.raises(ErrorTraduccion) as error:
            await traductor.traducir_comprobante(b"x", "image/png")

    assert "tardó" in str(error.value)
    assert len(solicitudes) == 2


async def test_error_transitorio_reintenta_una_vez():
    solicitudes = []

    async def handler(request):
        solicitudes.append(request)
        if len(solicitudes) == 1:
            return httpx.Response(
                503, json={"error": {"code": 503, "message": "unavailable"}}
            )
        return httpx.Response(200, json=respuesta_ok(json_valido()))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(
            api_key=CLAVE, cliente_http=cliente, timeout=1
        )
        resultado = await traductor.traducir_comprobante(b"x", "image/png")

    assert resultado.monto == 15000
    assert len(solicitudes) == 2


async def test_error_transitorio_dos_veces_falla():
    solicitudes = []

    async def handler(request):
        solicitudes.append(request)
        return httpx.Response(
            503, json={"error": {"code": 503, "message": "unavailable"}}
        )

    async with cliente_con(handler) as cliente:
        traductor = Traductor(
            api_key=CLAVE, cliente_http=cliente, timeout=1
        )
        with pytest.raises(ErrorTraduccion):
            await traductor.traducir_comprobante(b"x", "image/png")

    assert len(solicitudes) == 2


async def test_error_inesperado_de_la_api():
    async def handler(request):
        raise RuntimeError("boom")

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        with pytest.raises(ErrorTraduccion):
            await traductor.traducir_comprobante(b"x", "image/png")


async def test_mime_no_soportado():
    async def handler(request):
        raise AssertionError("No debería llamarse a la API")

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        with pytest.raises(ErrorTraduccion):
            await traductor.traducir_comprobante(b"x", "text/plain")


async def test_mime_jpg_se_normaliza():
    solicitudes = []

    async def handler(request):
        solicitudes.append(request)
        return httpx.Response(200, json=respuesta_ok(json_valido()))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        resultado = await traductor.traducir_comprobante(b"x", "image/jpg")

    assert resultado.monto == 15000
    payload = json.loads(solicitudes[0].content)
    mime = payload["contents"][0]["parts"][0]["inlineData"]["mimeType"]
    assert mime == "image/jpeg"


async def test_archivo_vacio():
    async def handler(request):
        raise AssertionError("No debería llamarse a la API")

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        with pytest.raises(ErrorTraduccion):
            await traductor.traducir_comprobante(b"", "image/png")


async def test_sin_api_key():
    async def handler(request):
        raise AssertionError("No debería llamarse a la API")

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key="", cliente_http=cliente)
        with pytest.raises(ErrorTraduccion) as error:
            await traductor.traducir_comprobante(b"x", "image/png")

    assert "GEMINI_API_KEY" in str(error.value)


async def test_balance_invalido():
    texto = json_valido(balance="otro")

    async def handler(request):
        return httpx.Response(200, json=respuesta_ok(texto))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(api_key=CLAVE, cliente_http=cliente)
        resultado = await traductor.traducir_comprobante(b"x", "image/png")

    assert resultado.balance is None
    assert "No se pudo determinar el balance." in resultado.advertencias


async def test_gestion_iniciar_traduccion(db_path):
    async def handler(request):
        return httpx.Response(200, json=respuesta_ok(json_valido()))

    async with cliente_con(handler) as cliente:
        traductor = Traductor(
            api_key=CLAVE, cliente_http=cliente, modelo="test"
        )
        gestion = Gestion(db_path, traductor=traductor)

        assert gestion.conocer_traductor() is traductor

        resultado = await gestion.iniciar_traduccion(
            b"x", "image/png", contexto="gym"
        )

    assert resultado["monto"] == 15000
    assert resultado["balance"] == "EGRESO"
    assert resultado["advertencias"] == []
