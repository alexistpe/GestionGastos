"""Punto de entrada del bot GestionGastos."""

from __future__ import annotations

import asyncio
import logging
import warnings
from logging.handlers import RotatingFileHandler

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    TypeHandler,
)
from telegram.warnings import PTBUserWarning

warnings.filterwarnings(
    "ignore",
    message="If 'per_message=False'.*",
    category=PTBUserWarning,
)

import config
from database import db
from handlers import (
    alerta_handler,
    analisis_handler,
    balance_handler,
    comprobante_handler,
    edicion_handler,
    etiqueta_handler,
    sistema_handler,
)
from modules.gestion import Gestion
from modules.persistencia import SQLitePersistence

logger = logging.getLogger(__name__)

COMANDOS = [
    BotCommand("start", "Iniciar el bot"),
    BotCommand("ayuda", "Guía de comandos"),
    BotCommand("analisis", "Análisis del mes o por rango"),
    BotCommand("alerta", "Configurar una alerta"),
    BotCommand("alertas", "Ver alertas activas"),
    BotCommand("etiqueta", "Crear una etiqueta"),
    BotCommand("etiquetas", "Listar etiquetas"),
    BotCommand("eliminar", "Eliminar una etiqueta"),
    BotCommand("editar", "Editar un comprobante"),
    BotCommand("borrar", "Borrar un comprobante"),
    BotCommand("cancelar", "Cancelar la operación actual"),
]


class _RedactarSecretos(logging.Filter):
    def __init__(self, secretos: list[str]) -> None:
        super().__init__()
        self._secretos = [secreto for secreto in secretos if secreto]

    def filter(self, record: logging.LogRecord) -> bool:
        mensaje = record.getMessage()
        redactado = mensaje
        for secreto in self._secretos:
            redactado = redactado.replace(secreto, "***")
        if redactado != mensaje:
            record.msg = redactado
            record.args = None
        return True


def configurar_logging() -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    nivel = getattr(logging, config.LOG_LEVEL, logging.INFO)
    formato = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s :: %(message)s"
    )

    archivo = RotatingFileHandler(
        config.LOG_DIR / "bot.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    archivo.setFormatter(formato)
    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    filtro = _RedactarSecretos(
        [config.TELEGRAM_BOT_TOKEN, config.GEMINI_API_KEY]
    )
    archivo.addFilter(filtro)
    consola.addFilter(filtro)

    logging.basicConfig(
        level=nivel,
        handlers=[archivo, consola],
        force=True,
    )
    # httpx registra la URL completa de Telegram, que incluye el token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def _solo_autorizado(update: Update, context) -> None:
    chat = update.effective_chat
    if (
        chat is not None
        and config.TELEGRAM_CHAT_ID is not None
        and chat.id != config.TELEGRAM_CHAT_ID
    ):
        raise ApplicationHandlerStop


async def _manejar_error(update, context) -> None:
    logger.error("Error no manejado", exc_info=context.error)
    try:
        if (
            update is not None
            and update.effective_chat is not None
            and update.effective_chat.id == config.TELEGRAM_CHAT_ID
            and update.effective_message is not None
        ):
            await update.effective_message.reply_text(
                "❌ Ocurrió un error inesperado. "
                "Probá de nuevo o usá /cancelar."
            )
    except Exception:  # pragma: no cover - defensivo
        logger.debug("No se pudo notificar el error al usuario")


def construir_aplicacion() -> Application:
    faltantes = config.validar_config()
    if faltantes:
        raise RuntimeError(
            "Faltan variables de entorno: " + ", ".join(faltantes)
        )

    db.init_db(config.DB_PATH)
    expiradas = db.limpiar_estados_expirados(
        ttl_horas=1, db_path=config.DB_PATH
    )
    persistencia = SQLitePersistence(db_path=config.DB_PATH)

    async def post_init(application: Application) -> None:
        try:
            await application.bot.set_my_commands(COMANDOS)
        except Exception:  # pragma: no cover - depende de la red
            logger.warning(
                "No se pudo configurar el menú de comandos", exc_info=True
            )
        for fila in expiradas:
            try:
                await application.bot.send_message(
                    chat_id=int(fila["chat_id"]),
                    text=(
                        "⏳ Tu sesión anterior expiró. "
                        "Podés empezar de nuevo."
                    ),
                )
            except Exception:  # pragma: no cover - defensivo
                logger.warning(
                    "No se pudo notificar la sesión expirada", exc_info=True
                )
        logger.info("Bot iniciado")

    aplicacion = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .persistence(persistencia)
        .post_init(post_init)
        .build()
    )
    aplicacion.bot_data["gestion"] = Gestion(config.DB_PATH)

    aplicacion.add_handler(
        TypeHandler(Update, _solo_autorizado), group=-1
    )
    aplicacion.add_handler(comprobante_handler.obtener_handler(), group=0)
    aplicacion.add_handler(edicion_handler.obtener_handler(), group=0)

    for handler in sistema_handler.obtener_handlers():
        aplicacion.add_handler(handler, group=1)
    for handler in balance_handler.obtener_handlers():
        aplicacion.add_handler(handler, group=1)
    for handler in analisis_handler.obtener_handlers():
        aplicacion.add_handler(handler, group=1)
    for handler in alerta_handler.obtener_handlers():
        aplicacion.add_handler(handler, group=1)
    for handler in etiqueta_handler.obtener_handlers():
        aplicacion.add_handler(handler, group=1)

    aplicacion.add_error_handler(_manejar_error)
    return aplicacion


def main() -> None:
    configurar_logging()
    aplicacion = construir_aplicacion()
    # Python 3.14 ya no crea un event loop implícito en el hilo principal.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        aplicacion.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        loop.close()


if __name__ == "__main__":
    main()
