"""Edición y borrado de comprobantes ya guardados."""

from __future__ import annotations

import logging
import re

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

import config
from database import db
from modules.gestion import ErrorGestion, Gestion
from utils import parsers
from utils import telegram as ui
from utils.parsers import ErrorParseo

logger = logging.getLogger(__name__)

ESPERANDO_SELECCION = 10
MOSTRANDO_COMPROBANTE = 11
ESPERANDO_VALOR = 12
CONFIRMANDO_BORRADO = 13
ESPERANDO_SELECCION_ETIQUETA = 14

CLAVE_EDICION = "edicion_comprobante"
RE_EDITAR = re.compile(r"^editar(?:\s+#?\d+)?$", re.IGNORECASE)
RE_BORRAR = re.compile(r"^borrar(?:\s+#?\d+)?$", re.IGNORECASE)


def _gestion(context: ContextTypes.DEFAULT_TYPE) -> Gestion:
    return context.application.bot_data["gestion"]


def _marcar(context: ContextTypes.DEFAULT_TYPE, update: Update) -> None:
    try:
        context.application.mark_data_for_update_persistence(
            chat_ids=update.effective_chat.id,
            user_ids=update.effective_user.id,
        )
    except Exception:  # pragma: no cover - defensivo
        logger.debug("No se pudo marcar user_data para persistencia")


def _parsear_id(update: Update, context: ContextTypes.DEFAULT_TYPE, comando: str):
    texto = (update.effective_message.text or "").strip()
    coincidencia = re.fullmatch(
        rf"/?{comando}(?:\s+#?(\d+))?", texto, re.IGNORECASE
    )
    if coincidencia:
        return int(coincidencia.group(1)) if coincidencia.group(1) else None

    if context.args:
        coincidencia = re.fullmatch(r"#?(\d+)", " ".join(context.args).strip())
        if coincidencia:
            return int(coincidencia.group(1))
    return None


def _otra_conversacion_activa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado = db.obtener_estado(
        update.effective_chat.id, _gestion(context).db_path
    )
    return estado and estado.get("nombre_conversacion") != "edicion"


async def _mostrar_ficha(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    id_comprobante: int,
    query=None,
    avisos: list[dict] | None = None,
) -> bool:
    comprobante = _gestion(context).obtener_comprobante(id_comprobante)
    if comprobante is None:
        texto = f"No existe el comprobante #{id_comprobante}."
        if query is not None:
            await query.edit_message_text(texto)
        else:
            await update.effective_message.reply_text(texto)
        return False

    texto = (
        f"{ui.formatear_comprobante(comprobante)}\n\n"
        "Elegí un campo para editar."
    )
    teclado = ui.construir_teclado_edicion(id_comprobante)
    if query is not None:
        await query.edit_message_text(texto, reply_markup=teclado)
    else:
        await update.effective_message.reply_text(texto, reply_markup=teclado)

    if avisos:
        await update.effective_message.reply_text(
            "\n\n".join(alerta["mensaje"] for alerta in avisos)
        )
    return True


async def iniciar_edicion(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if _otra_conversacion_activa(update, context):
        await update.effective_message.reply_text(
            "Hay otra operación en curso. Terminála o usá /cancelar."
        )
        return ConversationHandler.END

    context.user_data.pop("borrador_comprobante", None)
    id_comprobante = _parsear_id(update, context, "editar")
    gestion = _gestion(context)

    if id_comprobante is None:
        recientes = gestion.listar_comprobantes_recientes(10)
        if not recientes:
            await update.effective_message.reply_text(
                "No hay comprobantes para editar."
            )
            return ConversationHandler.END
        await update.effective_message.reply_text(
            "Elegí el comprobante a editar:",
            reply_markup=ui.construir_teclado_seleccion(recientes, "editar"),
        )
        return ESPERANDO_SELECCION

    if not await _mostrar_ficha(update, context, id_comprobante):
        return ConversationHandler.END
    return MOSTRANDO_COMPROBANTE


async def iniciar_borrado(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if _otra_conversacion_activa(update, context):
        await update.effective_message.reply_text(
            "Hay otra operación en curso. Terminála o usá /cancelar."
        )
        return ConversationHandler.END

    context.user_data.pop("borrador_comprobante", None)
    id_comprobante = _parsear_id(update, context, "borrar")
    gestion = _gestion(context)

    if id_comprobante is None:
        recientes = gestion.listar_comprobantes_recientes(10)
        if not recientes:
            await update.effective_message.reply_text(
                "No hay comprobantes para borrar."
            )
            return ConversationHandler.END
        await update.effective_message.reply_text(
            "Elegí el comprobante a borrar:",
            reply_markup=ui.construir_teclado_seleccion(recientes, "borrar"),
        )
        return ESPERANDO_SELECCION

    comprobante = gestion.obtener_comprobante(id_comprobante)
    if comprobante is None:
        await update.effective_message.reply_text(
            f"No existe el comprobante #{id_comprobante}."
        )
        return ConversationHandler.END

    await update.effective_message.reply_text(
        f"¿Borrar este comprobante?\n{ui.formatear_comprobante(comprobante)}",
        reply_markup=ui.construir_teclado_borrado(id_comprobante),
    )
    return CONFIRMANDO_BORRADO


async def seleccionar_comprobante(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    partes = query.data.split(":")
    if len(partes) < 3:
        return ESPERANDO_SELECCION

    accion = partes[1]
    if accion == "cancelar":
        await query.edit_message_text("Operación cancelada.")
        return ConversationHandler.END

    id_comprobante = int(partes[2])
    gestion = _gestion(context)

    if accion == "editar":
        if not await _mostrar_ficha(
            update, context, id_comprobante, query=query
        ):
            return ConversationHandler.END
        return MOSTRANDO_COMPROBANTE

    if accion == "borrar":
        comprobante = gestion.obtener_comprobante(id_comprobante)
        if comprobante is None:
            await query.edit_message_text(
                f"No existe el comprobante #{id_comprobante}."
            )
            return ConversationHandler.END
        await query.edit_message_text(
            "¿Borrar este comprobante?\n"
            f"{ui.formatear_comprobante(comprobante)}",
            reply_markup=ui.construir_teclado_borrado(id_comprobante),
        )
        return CONFIRMANDO_BORRADO

    return ESPERANDO_SELECCION


async def callback_edicion(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    partes = query.data.split(":")
    if len(partes) < 3:
        await query.answer()
        return MOSTRANDO_COMPROBANTE

    id_comprobante = int(partes[1])
    campo = partes[2]
    gestion = _gestion(context)

    if campo == "listo":
        context.user_data.pop(CLAVE_EDICION, None)
        _marcar(context, update)
        await query.answer()
        await query.edit_message_text("Edición finalizada.")
        return ConversationHandler.END

    if campo == "cancelar":
        context.user_data.pop(CLAVE_EDICION, None)
        _marcar(context, update)
        await query.answer()
        await query.edit_message_text("Edición cancelada.")
        return ConversationHandler.END

    comprobante = gestion.obtener_comprobante(id_comprobante)
    if comprobante is None:
        await query.answer("El comprobante ya no existe.", show_alert=True)
        return ConversationHandler.END

    if campo == "etiqueta":
        await query.answer()
        etiquetas = gestion.listar_etiquetas()
        await query.edit_message_text(
            "Elegí la nueva etiqueta:",
            reply_markup=ui.construir_teclado_etiquetas(
                etiquetas, f"edit:{id_comprobante}"
            ),
        )
        return ESPERANDO_SELECCION_ETIQUETA

    if campo == "pag":
        pagina = int(partes[3]) if len(partes) >= 4 else 0
        etiquetas = gestion.listar_etiquetas()
        await query.answer()
        await query.edit_message_reply_markup(
            reply_markup=ui.construir_teclado_etiquetas(
                etiquetas, f"edit:{id_comprobante}", pagina
            )
        )
        return ESPERANDO_SELECCION_ETIQUETA

    if campo == "sel":
        if len(partes) < 4:
            await query.answer()
            return ESPERANDO_SELECCION_ETIQUETA
        id_etiqueta = int(partes[3])
        try:
            resultado = gestion.actualizar_comprobante(
                id_comprobante, {"id_etiqueta": id_etiqueta}
            )
        except ErrorGestion as exc:
            await query.answer(str(exc), show_alert=True)
            return ESPERANDO_SELECCION_ETIQUETA
        await query.answer("Etiqueta actualizada.")
        await _mostrar_ficha(
            update,
            context,
            id_comprobante,
            query=query,
            avisos=resultado["avisos"],
        )
        return MOSTRANDO_COMPROBANTE

    if campo == "balance":
        nuevo = (
            "INGRESO" if comprobante["balance"] == "EGRESO" else "EGRESO"
        )
        try:
            resultado = gestion.actualizar_comprobante(
                id_comprobante, {"balance": nuevo}
            )
        except ErrorGestion as exc:
            await query.answer(str(exc), show_alert=True)
            return MOSTRANDO_COMPROBANTE
        await query.answer("Balance actualizado.")
        await _mostrar_ficha(
            update,
            context,
            id_comprobante,
            query=query,
            avisos=resultado["avisos"],
        )
        return MOSTRANDO_COMPROBANTE

    if campo in {"monto", "fecha", "destino"}:
        context.user_data[CLAVE_EDICION] = {
            "id": id_comprobante,
            "campo": campo,
        }
        _marcar(context, update)
        await query.answer()
        instrucciones = {
            "monto": "✏️ Enviá el nuevo monto (ej: 15000 o 15.000,50).",
            "fecha": "📅 Enviá la nueva fecha (ej: 15.11.26).",
            "destino": "📝 Enviá el nuevo destino. Usá '-' para vaciarlo.",
        }
        await query.edit_message_text(instrucciones[campo])
        return ESPERANDO_VALOR

    await query.answer()
    return MOSTRANDO_COMPROBANTE


async def esperar_valor(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    datos = context.user_data.get(CLAVE_EDICION)
    if not datos:
        return ConversationHandler.END

    id_comprobante = int(datos["id"])
    campo = datos["campo"]
    texto = (update.effective_message.text or "").strip()

    try:
        if campo == "monto":
            valor = parsers.parsear_monto(texto)
        elif campo == "fecha":
            valor = parsers.parsear_fecha(texto)
        else:
            valor = None if texto in {"", "-"} else texto[:200]
    except ErrorParseo as exc:
        await update.effective_message.reply_text(
            f"⚠️ {exc}\nEnviá un valor válido o /cancelar."
        )
        return ESPERANDO_VALOR

    try:
        resultado = _gestion(context).actualizar_comprobante(
            id_comprobante, {campo: valor}
        )
    except ErrorGestion as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return ESPERANDO_VALOR

    context.user_data.pop(CLAVE_EDICION, None)
    _marcar(context, update)
    await _mostrar_ficha(
        update,
        context,
        id_comprobante,
        avisos=resultado["avisos"],
    )
    return MOSTRANDO_COMPROBANTE


async def callback_borrado(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    partes = query.data.split(":")
    if len(partes) < 3:
        await query.answer()
        return CONFIRMANDO_BORRADO

    accion = partes[1]
    id_comprobante = int(partes[2])
    if accion == "no":
        await query.answer()
        await query.edit_message_text("Operación cancelada.")
        return ConversationHandler.END

    try:
        _gestion(context).eliminar_comprobante(id_comprobante)
    except ErrorGestion as exc:
        await query.answer(str(exc), show_alert=True)
        return ConversationHandler.END

    await query.answer("Eliminado.")
    await query.edit_message_text(
        f"🗑️ Comprobante #{id_comprobante} eliminado."
    )
    return ConversationHandler.END


async def ayuda_estado(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.effective_message.reply_text(
        "Usá los botones de la lista o de la ficha, o /cancelar para salir."
    )
    return None


async def cancelar_edicion(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data.pop(CLAVE_EDICION, None)
    _marcar(context, update)
    db.eliminar_estado(update.effective_chat.id, _gestion(context).db_path)
    await update.effective_message.reply_text("❌ Edición cancelada.")
    return ConversationHandler.END


async def sesion_expirada(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data.pop(CLAVE_EDICION, None)
    chat_id = (
        update.effective_chat.id
        if update and update.effective_chat
        else config.TELEGRAM_CHAT_ID
    )
    if chat_id:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⏳ La sesión de edición expiró.",
            )
        except Exception:  # pragma: no cover - defensivo
            logger.warning("No se pudo notificar la sesión expirada")
    return ConversationHandler.END


def obtener_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("editar", iniciar_edicion),
            CommandHandler("borrar", iniciar_borrado),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(RE_EDITAR),
                iniciar_edicion,
            ),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(RE_BORRAR),
                iniciar_borrado,
            ),
        ],
        states={
            ESPERANDO_SELECCION: [
                CallbackQueryHandler(
                    seleccionar_comprobante, pattern=r"^sel:"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, ayuda_estado
                ),
            ],
            MOSTRANDO_COMPROBANTE: [
                CallbackQueryHandler(callback_edicion, pattern=r"^edit:"),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, ayuda_estado
                ),
            ],
            ESPERANDO_VALOR: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, esperar_valor
                ),
            ],
            ESPERANDO_SELECCION_ETIQUETA: [
                CallbackQueryHandler(callback_edicion, pattern=r"^edit:"),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, ayuda_estado
                ),
            ],
            CONFIRMANDO_BORRADO: [
                CallbackQueryHandler(
                    callback_borrado, pattern=r"^borrar:"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, ayuda_estado
                ),
            ],
            ConversationHandler.TIMEOUT: [
                TypeHandler(Update, sesion_expirada),
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar_edicion),
            MessageHandler(
                filters.Regex(r"^/?cancelar$"), cancelar_edicion
            ),
        ],
        name="edicion",
        persistent=True,
        conversation_timeout=3600,
    )
