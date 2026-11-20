"""Comandos de análisis financiero."""

from __future__ import annotations

import re
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from modules.gestion import ErrorGestion
from utils import parsers
from utils import telegram as ui
from utils.parsers import ErrorParseo

PATRON_ANALISIS = re.compile(
    r"^/?analisis(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE
)


async def manejar_analisis(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        datos = parsers.parsear_comando(update.effective_message.text or "")
    except ErrorParseo as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    if not datos or datos.get("tipo") != "analisis":
        return

    gestion = context.application.bot_data["gestion"]
    try:
        if datos.get("desde") is None:
            resumen = gestion.generar_resumen("MENSUAL")
        else:
            resumen = gestion.generar_resumen(
                "RANGO",
                desde=datos["desde"],
                hasta=datos.get("hasta") or date.today().isoformat(),
            )
    except ErrorGestion as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    await ui.enviar_texto(update, resumen.a_texto())


def obtener_handlers() -> list[MessageHandler]:
    return [
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ANALISIS),
            manejar_analisis,
        )
    ]
