"""Configuración y listado de alertas."""

from __future__ import annotations

import re

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from modules.gestion import ErrorGestion
from utils import parsers
from utils import telegram as ui
from utils.parsers import ErrorParseo

PATRON_ALERTAS = re.compile(r"^/?alertas(?:@\w+)?$", re.IGNORECASE)
PATRON_ALERTA = re.compile(
    r"^/?alerta(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE
)


async def manejar_alerta(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        datos = parsers.parsear_comando(update.effective_message.text or "")
    except ErrorParseo as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    if not datos or datos.get("tipo") != "alerta":
        return

    gestion = context.application.bot_data["gestion"]
    try:
        if datos["subtipo"] == "ETIQUETA":
            aviso = gestion.configurar_alerta_etiqueta(
                datos["etiqueta"], datos["monto"]
            )
        else:
            aviso = gestion.configurar_alerta_total(datos["monto"])
    except ErrorGestion as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    await update.effective_message.reply_text(
        f"✅ Alerta configurada\n{ui.formatear_alerta(aviso)}"
    )


async def listar_alertas(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    avisos = context.application.bot_data["gestion"].listar_alertas()
    if not avisos:
        await update.effective_message.reply_text(
            "No hay alertas activas."
        )
        return

    lineas = ["🚨 Alertas activas:"]
    lineas.extend(f"• {ui.formatear_alerta(aviso)}" for aviso in avisos)
    await ui.enviar_texto(update, "\n".join(lineas))


def obtener_handlers() -> list[MessageHandler]:
    return [
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ALERTAS),
            listar_alertas,
        ),
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ALERTA),
            manejar_alerta,
        ),
    ]
