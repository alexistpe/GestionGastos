"""Comandos generales del bot."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database import db
from utils import telegram as ui


async def start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.effective_message.reply_text(ui.TEXTO_BIENVENIDA)


async def ayuda(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await ui.enviar_texto(update, ui.TEXTO_AYUDA)


async def cancelar_global(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    gestion = context.application.bot_data["gestion"]
    db.eliminar_estado(update.effective_chat.id, gestion.db_path)
    await update.effective_message.reply_text(
        "No hay ninguna operación en curso."
    )


def obtener_handlers() -> list[CommandHandler]:
    return [
        CommandHandler("start", start),
        CommandHandler(["ayuda", "comandos"], ayuda),
        CommandHandler("cancelar", cancelar_global),
    ]
