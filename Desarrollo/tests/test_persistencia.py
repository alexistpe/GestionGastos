from modules.persistencia import SQLitePersistence


async def test_estado_y_user_data_roundtrip(db_path):
    persistencia = SQLitePersistence(db_path=db_path)

    await persistencia.update_user_data(123, {"borrador": {"monto": 100}})

    assert await persistencia.get_conversations("comprobante") == {}
    assert (await persistencia.get_user_data())[123] == {
        "borrador": {"monto": 100}
    }

    await persistencia.update_conversation("comprobante", (123, 123), 2)

    assert await persistencia.get_conversations("comprobante") == {
        (123, 123): 2
    }
    assert (await persistencia.get_user_data())[123]["borrador"]["monto"] == 100

    await persistencia.update_conversation("comprobante", (123, 123), None)

    assert await persistencia.get_conversations("comprobante") == {}
    assert await persistencia.get_user_data() == {}


async def test_conversaciones_distingue_nombre(db_path):
    persistencia = SQLitePersistence(db_path=db_path)

    await persistencia.update_conversation("comprobante", (1, 1), 2)

    assert await persistencia.get_conversations("comprobante") == {(1, 1): 2}
    assert await persistencia.get_conversations("edicion") == {}


async def test_drop_user_data_conserva_estado(db_path):
    persistencia = SQLitePersistence(db_path=db_path)

    await persistencia.update_user_data(2, {"x": 1})
    await persistencia.update_conversation("edicion", (2, 2), 11)
    await persistencia.drop_user_data(2)

    assert await persistencia.get_conversations("edicion") == {(2, 2): 11}
    assert await persistencia.get_user_data() == {}


async def test_user_data_vacio_sin_estado_no_crea_fila(db_path):
    persistencia = SQLitePersistence(db_path=db_path)

    await persistencia.update_user_data(999, {})

    assert await persistencia.get_user_data() == {}
    assert await persistencia.get_conversations("comprobante") == {}


async def test_user_data_vacio_conserva_estado(db_path):
    persistencia = SQLitePersistence(db_path=db_path)

    await persistencia.update_conversation("comprobante", (3, 3), 1)
    await persistencia.update_user_data(3, {})

    assert await persistencia.get_conversations("comprobante") == {(3, 3): 1}
    assert (await persistencia.get_user_data())[3] == {}


async def test_estado_string_se_conserva(db_path):
    persistencia = SQLitePersistence(db_path=db_path)

    await persistencia.update_conversation("comprobante", (4, 4), "LISTO")

    assert await persistencia.get_conversations("comprobante") == {
        (4, 4): "LISTO"
    }


def test_configuracion_store_data():
    persistencia = SQLitePersistence()

    assert persistencia.store_data.user_data is True
    assert persistencia.store_data.chat_data is False
    assert persistencia.store_data.bot_data is False
    assert persistencia.store_data.callback_data is False
