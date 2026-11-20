import logging

import config
import main
from modules.gestion import Gestion
from modules.persistencia import SQLitePersistence


def test_construir_aplicacion(db_path, monkeypatch):
    monkeypatch.setattr(
        config,
        "TELEGRAM_BOT_TOKEN",
        "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
    )
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", 123456)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake")
    monkeypatch.setattr(config, "DB_PATH", db_path)

    aplicacion = main.construir_aplicacion()

    assert isinstance(aplicacion.persistence, SQLitePersistence)
    assert isinstance(aplicacion.bot_data["gestion"], Gestion)
    assert aplicacion.persistence.store_data.user_data is True
    assert aplicacion.persistence.store_data.chat_data is False
    assert aplicacion.job_queue is not None

    grupos = set(aplicacion.handlers)
    assert {-1, 0, 1}.issubset(grupos)
    assert len(aplicacion.handlers[0]) == 2
    assert len(aplicacion.handlers[1]) >= 5


def test_redactar_secretos_en_logs():
    filtro = main._RedactarSecretos(["TOKEN123", "KEY456"])
    registro = logging.LogRecord(
        "test",
        logging.INFO,
        __file__,
        1,
        "url https://api.telegram.org/botTOKEN123/getMe key KEY456",
        None,
        None,
    )

    assert filtro.filter(registro) is True
    mensaje = registro.getMessage()
    assert "TOKEN123" not in mensaje
    assert "KEY456" not in mensaje
    assert mensaje.count("***") == 2


def test_validar_config_faltantes(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", None)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")

    faltantes = config.validar_config()

    assert "TELEGRAM_BOT_TOKEN" in faltantes
    assert "TELEGRAM_CHAT_ID" in faltantes
    assert "GEMINI_API_KEY" in faltantes
