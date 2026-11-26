"""Comandos de ahorro: reporte y saldo inicial."""

from __future__ import annotations

import re

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from modules.gestion import ErrorGestion
from utils import parsers
from utils import telegram as ui
from utils.formato import formatear_monto
from utils.parsers import ErrorParseo

PATRON_AHORRO = re.compile(
    r"^/?ahorro(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE
)


async def manejar_ahorro(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        datos = parsers.parsear_comando(update.effective_message.text or "")
    except ErrorParseo as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    if not datos or datos.get("tipo") not in {
        "reporte_ahorro",
        "ahorro_inicial",
    }:
        return

    gestion = context.application.bot_data["gestion"]

    if datos["tipo"] == "reporte_ahorro":
        try:
            resumen = gestion.generar_resumen("MENSUAL")
        except ErrorGestion as exc:
            await update.effective_message.reply_text(f"⚠️ {exc}")
            return
        await ui.enviar_texto(update, resumen.a_texto_ahorro())
        return

    if datos.get("monto") is None:
        actual = gestion.obtener_saldo_inicial_ahorro()
        await update.effective_message.reply_text(
            f"🐷 Saldo inicial de ahorro: {formatear_monto(actual)}\n"
            "Para cambiarlo: ahorro inicial monto"
        )
        return

    try:
        valor = gestion.configurar_saldo_inicial_ahorro(datos["monto"])
    except ErrorGestion as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    await update.effective_message.reply_text(
        "✅ Saldo inicial de ahorro actualizado: "
        f"{formatear_monto(valor)}\n"
        "Los análisis acumulados se recalculan."
    )


def obtener_handlers() -> list[MessageHandler]:
    return [
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_AHORRO),
            manejar_ahorro,
        )
    ]
