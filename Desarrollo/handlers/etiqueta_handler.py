"""Gestión de etiquetas: creación, listado y eliminación."""

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

from database import db
from modules.gestion import ErrorGestion
from utils import parsers
from utils import telegram as ui
from utils.parsers import ErrorParseo

PATRON_ETIQUETAS = re.compile(r"^/?etiquetas(?:@\w+)?$", re.IGNORECASE)
PATRON_ETIQUETA = re.compile(
    r"^/?etiqueta(?:@\w+)?(?:\s+.*)?$", re.IGNORECASE
)
PATRON_ELIMINAR = re.compile(
    r"^/?eliminar(?:@\w+)?\s+etiqueta(?:\s+.*)?$", re.IGNORECASE
)
PATRON_CALLBACK = r"^(del:|del_ok:|del_no:)"


def _gestion(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data["gestion"]


async def crear_etiqueta(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        datos = parsers.parsear_comando(update.effective_message.text or "")
    except ErrorParseo as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    if not datos or datos.get("tipo") != "crear_etiqueta":
        return

    try:
        etiqueta = _gestion(context).crear_etiqueta(datos["nombre"])
    except ErrorGestion as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return

    await update.effective_message.reply_text(
        f"✅ Etiqueta creada: {etiqueta['nombre']}"
    )


async def listar_etiquetas(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    etiquetas = _gestion(context).listar_etiquetas()
    if not etiquetas:
        await update.effective_message.reply_text("No hay etiquetas.")
        return

    lineas = ["🏷️ Etiquetas:"]
    for etiqueta in etiquetas:
        sufijo = " (rutina)" if etiqueta["es_rutina"] else ""
        lineas.append(f"• {etiqueta['nombre']}{sufijo}")
    await ui.enviar_texto(update, "\n".join(lineas))


async def eliminar_etiqueta(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    gestion = _gestion(context)
    try:
        datos = parsers.parsear_comando(update.effective_message.text or "")
    except ErrorParseo:
        datos = None

    if datos and datos.get("tipo") == "eliminar_etiqueta":
        try:
            nombre = gestion.eliminar_etiqueta(datos["nombre"])
        except ErrorGestion as exc:
            await update.effective_message.reply_text(f"⚠️ {exc}")
            return
        await update.effective_message.reply_text(
            f"🗑️ Etiqueta '{nombre}' eliminada."
        )
        return

    etiquetas = gestion.listar_etiquetas()
    if not etiquetas:
        await update.effective_message.reply_text(
            "No hay etiquetas para eliminar."
        )
        return
    await update.effective_message.reply_text(
        "Elegí la etiqueta a eliminar:",
        reply_markup=ui.construir_teclado_etiquetas(etiquetas, "del"),
    )


async def callback_eliminar_etiqueta(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    datos = query.data
    gestion = _gestion(context)

    if datos.startswith("del:sel:"):
        id_etiqueta = int(datos.split(":")[2])
        etiqueta = db.obtener_etiqueta(id_etiqueta, gestion.db_path)
        if etiqueta is None:
            await query.answer("La etiqueta ya no existe.", show_alert=True)
            return
        await query.answer()
        await query.edit_message_text(
            f"¿Eliminar la etiqueta '{etiqueta['nombre']}'?\n"
            "También se eliminarán sus alertas.",
            reply_markup=ui.construir_teclado_confirmar_eliminar(id_etiqueta),
        )
        return

    if datos.startswith("del:pag:"):
        pagina = int(datos.split(":")[2])
        etiquetas = gestion.listar_etiquetas()
        await query.answer()
        await query.edit_message_reply_markup(
            reply_markup=ui.construir_teclado_etiquetas(
                etiquetas, "del", pagina
            )
        )
        return

    if datos == "del:cancelar":
        await query.answer()
        await query.edit_message_text("Operación cancelada.")
        return

    if datos.startswith("del_no:"):
        await query.answer()
        await query.edit_message_text("Operación cancelada.")
        return

    if datos.startswith("del_ok:"):
        id_etiqueta = int(datos.split(":")[1])
        etiqueta = db.obtener_etiqueta(id_etiqueta, gestion.db_path)
        if etiqueta is None:
            await query.answer("La etiqueta ya no existe.", show_alert=True)
            return
        try:
            gestion.eliminar_etiqueta(etiqueta["nombre"])
        except ErrorGestion as exc:
            await query.answer(str(exc), show_alert=True)
            return
        await query.answer("Eliminada.")
        await query.edit_message_text(
            f"🗑️ Etiqueta '{etiqueta['nombre']}' eliminada."
        )
        return

    await query.answer()


def obtener_handlers() -> list[Any]:
    return [
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ETIQUETAS),
            listar_etiquetas,
        ),
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ETIQUETA),
            crear_etiqueta,
        ),
        MessageHandler(
            filters.TEXT & filters.Regex(PATRON_ELIMINAR),
            eliminar_etiqueta,
        ),
        CallbackQueryHandler(
            callback_eliminar_etiqueta, pattern=PATRON_CALLBACK
        ),
    ]
