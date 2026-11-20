from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

from telegram import Chat, Message, Update, User

from database import db
from handlers import (
    alerta_handler,
    analisis_handler,
    balance_handler,
    etiqueta_handler,
)
from modules.gestion import Gestion


class FakeApplication:
    def __init__(self, gestion):
        self.bot_data = {"gestion": gestion}


class FakeContext:
    def __init__(self, gestion):
        self.application = FakeApplication(gestion)


def crear_update(texto: str, chat_id: int = 123, user_id: int = 123) -> Update:
    usuario = User(id=user_id, first_name="Test", is_bot=False)
    chat = Chat(id=chat_id, type="private")
    mensaje = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=chat,
        from_user=usuario,
        text=texto,
    )
    return Update(update_id=1, message=mensaje)


def textos_de_reply(reply) -> list[str]:
    return [
        llamada.args[0]
        for llamada in reply.await_args_list
        if llamada.args
    ]


async def test_balance_handler_registra(db_path):
    gestion = Gestion(db_path)
    update = crear_update("+ cuota 850000")
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await balance_handler.manejar_balance(update, context)

    comprobantes = db.listar_comprobantes(db_path)
    assert len(comprobantes) == 1
    assert comprobantes[0]["etiqueta"] == "cuota"
    assert comprobantes[0]["balance"] == "INGRESO"
    assert comprobantes[0]["monto"] == 850000
    assert reply.await_count >= 1


async def test_balance_handler_etiqueta_inexistente(db_path):
    gestion = Gestion(db_path)
    update = crear_update("- noexiste 1000")
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await balance_handler.manejar_balance(update, context)

    assert any("no existe" in texto for texto in textos_de_reply(reply))


async def test_analisis_handler(db_path):
    gestion = Gestion(db_path)
    hoy = date.today()
    inicio = hoy.replace(day=1)
    gestion.registrar_comprobante(
        850000, "INGRESO", etiqueta="cuota", fecha=inicio
    )
    gestion.registrar_comprobante(
        15000, "EGRESO", etiqueta="nafta", fecha=hoy
    )

    update = crear_update("analisis")
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await analisis_handler.manejar_analisis(update, context)

    textos = textos_de_reply(reply)
    assert any("Análisis del mes" in texto for texto in textos)
    assert any("$835.000,00" in texto for texto in textos)


async def test_alerta_handler_configura(db_path):
    gestion = Gestion(db_path)
    update = crear_update("alerta nafta 15000")
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await alerta_handler.manejar_alerta(update, context)

    avisos = gestion.listar_alertas()
    assert len(avisos) == 1
    assert avisos[0]["etiqueta"] == "nafta"
    assert reply.await_count >= 1


async def test_listar_alertas(db_path):
    gestion = Gestion(db_path)
    gestion.configurar_alerta_total(100000)
    update = crear_update("alertas")
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await alerta_handler.listar_alertas(update, context)

    assert any("Gasto total" in texto for texto in textos_de_reply(reply))


async def test_etiqueta_handler_crear_y_listar(db_path):
    gestion = Gestion(db_path)
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ):
        await etiqueta_handler.crear_etiqueta(
            crear_update("etiqueta supermercado"), context
        )

    assert db.obtener_etiqueta_por_nombre("supermercado", db_path) is not None

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await etiqueta_handler.listar_etiquetas(
            crear_update("etiquetas"), context
        )

    assert any("supermercado" in texto for texto in textos_de_reply(reply))


async def test_eliminar_etiqueta_por_nombre(db_path):
    gestion = Gestion(db_path)
    gestion.crear_etiqueta("temporal")
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ):
        await etiqueta_handler.eliminar_etiqueta(
            crear_update("eliminar etiqueta temporal"), context
        )

    assert db.obtener_etiqueta_por_nombre("temporal", db_path) is None


async def test_eliminar_etiqueta_sin_nombre_muestra_selector(db_path):
    gestion = Gestion(db_path)
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await etiqueta_handler.eliminar_etiqueta(
            crear_update("eliminar etiqueta"), context
        )

    assert reply.await_count == 1
    assert reply.await_args.kwargs.get("reply_markup") is not None
