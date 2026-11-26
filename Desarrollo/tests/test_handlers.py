from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

from telegram import CallbackQuery, Chat, Message, Update, User

from database import db
from handlers import (
    ahorro_handler,
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


def crear_update_callback(
    data: str, chat_id: int = 123, user_id: int = 123
) -> Update:
    usuario = User(id=user_id, first_name="Test", is_bot=False)
    chat = Chat(id=chat_id, type="private")
    mensaje = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=chat,
        from_user=usuario,
        text="mensaje",
    )
    callback = CallbackQuery(
        id="cb-1",
        from_user=usuario,
        chat_instance="chat-instance",
        message=mensaje,
        data=data,
    )
    return Update(update_id=1, callback_query=callback)


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


async def test_ahorro_handler_saldo_inicial_y_reporte(db_path):
    gestion = Gestion(db_path)
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await ahorro_handler.manejar_ahorro(
            crear_update("ahorro inicial 100000"), context
        )

    assert gestion.obtener_saldo_inicial_ahorro() == 100000
    assert any("Saldo inicial" in texto for texto in textos_de_reply(reply))

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await ahorro_handler.manejar_ahorro(crear_update("ahorro"), context)

    textos = textos_de_reply(reply)
    assert any(
        "Depositado" in texto and "Extraído" in texto for texto in textos
    )

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await ahorro_handler.manejar_ahorro(
            crear_update("ahorro inicial"), context
        )

    assert any(
        "Saldo inicial de ahorro" in texto
        for texto in textos_de_reply(reply)
    )


async def test_eliminar_alerta_selector_y_confirmacion(db_path):
    gestion = Gestion(db_path)
    aviso = gestion.configurar_alerta_total(100000)
    context = FakeContext(gestion)

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await alerta_handler.eliminar_alerta(
            crear_update("eliminar alerta"), context
        )

    markup = reply.await_args.kwargs.get("reply_markup")
    assert markup is not None
    callbacks = [
        boton.callback_data
        for fila in markup.inline_keyboard
        for boton in fila
    ]
    assert f"del_aviso:{aviso['id']}" in callbacks
    assert "del_aviso:cancelar" in callbacks

    with patch.object(
        Message, "reply_text", new_callable=AsyncMock
    ) as reply:
        await alerta_handler.eliminar_alerta(
            crear_update(f"eliminar alerta {aviso['id']}"), context
        )

    assert reply.await_args.kwargs.get("reply_markup") is not None


async def test_eliminar_alerta_callback_ok(db_path):
    gestion = Gestion(db_path)
    aviso = gestion.configurar_alerta_total(100000)
    context = FakeContext(gestion)
    update = crear_update_callback(f"del_aviso_ok:{aviso['id']}")

    with patch.object(
        CallbackQuery, "answer", new_callable=AsyncMock
    ) as answer, patch.object(
        CallbackQuery, "edit_message_text", new_callable=AsyncMock
    ) as edit:
        await alerta_handler.callback_eliminar_alerta(update, context)

    assert gestion.conocer_aviso(aviso["id"]) is None
    answer.assert_awaited()
    edit.assert_awaited()
    assert "eliminada" in edit.await_args.args[0]
