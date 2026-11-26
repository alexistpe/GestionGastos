"""Configuración, listado y eliminación de alertas."""

from __future__ import annotations

import re
from typing import Any

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from modules.gestion import ErrorGestion
from utils import parsers
from utils import telegram as ui
from utils.parsers import ErrorParseo

PATRON_ALERTAS = re.compile(r"^/?alertas(?:@\w+)?$", re.IGNORECASE)
PATRON_ALERTA = re.compile(
    r"^/?alerta(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE
)
PATRON_ELIMINAR_ALERTA = re.compile(
    r"^/?eliminar(?:@\w+)?\s+alerta(?:\s+.*)?$", re.IGNORECASE
)
PATRON_CALLBACK_ELIMINAR = (
    r"^(del_aviso:|del_aviso_ok:|del_aviso_no:)"
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
    lineas.extend(
        f"• {ui.formatear_alerta(aviso, incluir_id=True)}"
        for aviso in avisos
    )
    lineas.append("Para eliminar una alerta: eliminar alerta ID")
    await ui.enviar_texto(update, "\n".join(lineas))


async def eliminar_alerta(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        datos = parsers.parsear_comando(update.effective_message.text or "")
    except ErrorParseo as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    if not datos or datos.get("tipo") != "eliminar_alerta":
        return

    gestion = context.application.bot_data["gestion"]

    if datos.get("id") is None:
        avisos = gestion.listar_alertas()
        if not avisos:
            await update.effective_message.reply_text(
                "No hay alertas activas para eliminar."
            )
            return
        await update.effective_message.reply_text(
            "Elegí la alerta a eliminar:",
            reply_markup=ui.construir_teclado_alertas(avisos),
        )
        return

    id_aviso = int(datos["id"])
    aviso = gestion.conocer_aviso(id_aviso)
    if aviso is None:
        await update.effective_message.reply_text(
            f"No existe la alerta #{id_aviso}."
        )
        return

    await update.effective_message.reply_text(
        "¿Eliminar esta alerta?\n"
        f"{ui.formatear_alerta(aviso, incluir_id=True)}",
        reply_markup=ui.construir_teclado_confirmar_eliminar_alerta(id_aviso),
    )


async def callback_eliminar_alerta(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    datos = query.data or ""
    gestion = context.application.bot_data["gestion"]

    if datos == "del_aviso:cancelar":
        await query.answer()
        await query.edit_message_text("Operación cancelada.")
        return

    if datos.startswith("del_aviso:"):
        id_aviso = int(datos.split(":")[1])
        aviso = gestion.conocer_aviso(id_aviso)
        if aviso is None:
            await query.answer("La alerta ya no existe.", show_alert=True)
            return
        await query.answer()
        await query.edit_message_text(
            "¿Eliminar esta alerta?\n"
            f"{ui.formatear_alerta(aviso, incluir_id=True)}",
            reply_markup=ui.construir_teclado_confirmar_eliminar_alerta(
                id_aviso
            ),
        )
        return

    if datos.startswith("del_aviso_no:"):
        await query.answer()
        await query.edit_message_text("Operación cancelada.")
        return

    if datos.startswith("del_aviso_ok:"):
        id_aviso = int(datos.split(":")[1])
        try:
            gestion.eliminar_alerta(id_aviso)
        except ErrorGestion as exc:
            await query.answer(str(exc), show_alert=True)
            return
        await query.answer("Eliminada.")
        await query.edit_message_text(
            f"🗑️ Alerta #{id_aviso} eliminada."
        )
        return

    await query.answer()


def obtener_handlers() -> list[Any]:
    return [
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ALERTAS),
            listar_alertas,
        ),
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ALERTA),
            manejar_alerta,
        ),
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ELIMINAR_ALERTA),
            eliminar_alerta,
        ),
        CallbackQueryHandler(
            callback_eliminar_alerta, pattern=PATRON_CALLBACK_ELIMINAR
        ),
    ]
