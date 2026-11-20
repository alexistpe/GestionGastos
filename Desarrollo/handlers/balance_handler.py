"""Balances manuales por texto (ingresos y egresos)."""

from __future__ import annotations

import re

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from modules.gestion import ErrorGestion
from utils import parsers
from utils import telegram as ui
from utils.parsers import ErrorParseo

PATRON_BALANCE = re.compile(r"^\s*[+-]")


async def manejar_balance(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        datos = parsers.parsear_comando_balance(
            update.effective_message.text or ""
        )
    except ErrorParseo as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    if datos is None:
        return

    gestion = context.application.bot_data["gestion"]
    try:
        resultado = gestion.registrar_comprobante(
            monto=datos["monto"],
            balance=datos["balance"],
            etiqueta=datos["etiqueta"],
        )
    except ErrorGestion as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    await update.effective_message.reply_text(
        "✅ Balance registrado\n"
        f"{ui.formatear_comprobante(resultado['comprobante'])}"
    )
    if resultado["avisos"]:
        await update.effective_message.reply_text(
            "\n\n".join(alerta["mensaje"] for alerta in resultado["avisos"])
        )


def obtener_handlers() -> list[MessageHandler]:
    return [
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_BALANCE),
            manejar_balance,
        )
    ]
