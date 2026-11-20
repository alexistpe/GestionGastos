"""Registro de comprobantes y edición previa a la confirmación."""

from __future__ import annotations

import logging
from typing import Any

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
from modules.traductor import ErrorTraduccion
from utils import parsers
from utils import telegram as ui
from utils.parsers import ErrorParseo

logger = logging.getLogger(__name__)

ESPERANDO_SELEC_ETIQUETA = 1
ESPERANDO_CONFIRMACION = 2
CORRIGIENDO_MONTO = 3
CORRIGIENDO_FECHA = 4
CORRIGIENDO_DESTINO = 5

DRAFT_KEY = "borrador_comprobante"
MIME_PERMITIDOS = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
FILTRO_ARCHIVO = (
    filters.PHOTO | filters.Document.IMAGE | filters.Document.PDF
)


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


def _guardar_borrador(
    context: ContextTypes.DEFAULT_TYPE, update: Update, borrador: dict[str, Any]
) -> None:
    context.user_data[DRAFT_KEY] = borrador
    _marcar(context, update)


def _limpiar_borrador(
    context: ContextTypes.DEFAULT_TYPE, update: Update
) -> None:
    context.user_data.pop(DRAFT_KEY, None)
    _marcar(context, update)
    db.eliminar_estado(update.effective_chat.id, _gestion(context).db_path)


def _faltantes(borrador: dict[str, Any]) -> list[str]:
    faltantes: list[str] = []
    if not borrador.get("fecha"):
        faltantes.append("fecha")
    if borrador.get("monto") is None:
        faltantes.append("monto")
    if not borrador.get("balance"):
        faltantes.append("balance")
    if not borrador.get("id_etiqueta"):
        faltantes.append("etiqueta")
    return faltantes


def _draft_completo(borrador: dict[str, Any] | None) -> bool:
    return bool(borrador) and not _faltantes(borrador)


async def _descargar(update: Update) -> tuple[bytes, str, str]:
    mensaje = update.effective_message
    if mensaje.photo:
        foto = mensaje.photo[-1]
        if foto.file_size and foto.file_size > 20 * 1024 * 1024:
            raise ErrorTraduccion("El archivo supera el límite de 20 MB.")
        archivo = await foto.get_file()
        contenido = bytes(await archivo.download_as_bytearray())
        return contenido, "image/jpeg", mensaje.caption or ""

    documento = mensaje.document
    if documento is None:
        raise ErrorTraduccion("No se encontró el archivo del comprobante.")
    if documento.file_size and documento.file_size > 20 * 1024 * 1024:
        raise ErrorTraduccion("El archivo supera el límite de 20 MB.")

    mime = (documento.mime_type or "").split(";")[0].strip().lower()
    if mime == "image/jpg":
        mime = "image/jpeg"
    if mime not in MIME_PERMITIDOS:
        nombre = (documento.file_name or "").lower()
        if nombre.endswith(".pdf"):
            mime = "application/pdf"
        elif nombre.endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"
        elif nombre.endswith(".png"):
            mime = "image/png"
        elif nombre.endswith(".webp"):
            mime = "image/webp"
        else:
            raise ErrorTraduccion(
                "Formato no soportado. Enviá una imagen JPG/PNG/WEBP o un PDF."
            )

    archivo = await documento.get_file()
    contenido = bytes(await archivo.download_as_bytearray())
    return contenido, mime, mensaje.caption or ""


async def _mostrar_selector(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    borrador: dict[str, Any],
    query=None,
    pagina: int = 0,
) -> None:
    etiquetas = _gestion(context).listar_etiquetas()
    texto = f"{ui.formatear_borrador(borrador)}\n\nElegí una etiqueta:"
    teclado = ui.construir_teclado_etiquetas(etiquetas, "draft", pagina)
    if query is not None:
        await query.edit_message_text(texto, reply_markup=teclado)
    else:
        await update.effective_message.reply_text(texto, reply_markup=teclado)


async def _mostrar_confirmacion(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    borrador: dict[str, Any],
    query=None,
) -> None:
    texto = ui.formatear_borrador(borrador)
    teclado = ui.construir_teclado_confirmacion()
    if query is not None:
        await query.edit_message_text(texto, reply_markup=teclado)
    else:
        await update.effective_message.reply_text(texto, reply_markup=teclado)


async def _enviar_avisos(
    update: Update, avisos: list[dict[str, Any]]
) -> None:
    if not avisos:
        return
    texto = "\n\n".join(alerta["mensaje"] for alerta in avisos)
    await update.effective_message.reply_text(texto)


async def recibir_comprobante(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    gestion = _gestion(context)
    chat_id = update.effective_chat.id
    estado = db.obtener_estado(chat_id, gestion.db_path)
    if estado and estado.get("nombre_conversacion") != "comprobante":
        await update.effective_message.reply_text(
            "Hay una edición en curso. Terminála o usá /cancelar."
        )
        return ConversationHandler.END

    try:
        contenido, mime, caption = await _descargar(update)
    except ErrorTraduccion as exc:
        await update.effective_message.reply_text(f"⚠️ {exc}")
        return ConversationHandler.END

    await update.effective_message.reply_text(
        "📎 Comprobante recibido. Procesando..."
    )

    etiquetas = gestion.listar_etiquetas()
    nombres = [etiqueta["nombre"] for etiqueta in etiquetas]
    nombre_etiqueta = parsers.extraer_etiqueta_de_caption(caption, nombres)
    etiqueta = next(
        (e for e in etiquetas if e["nombre"] == nombre_etiqueta), None
    )

    try:
        extraido = await gestion.iniciar_traduccion(
            contenido, mime, contexto=caption
        )
    except ErrorTraduccion as exc:
        await update.effective_message.reply_text(
            f"❌ {exc}\n\n"
            "Podés reenviarlo o cargarlo manualmente con: - etiqueta monto"
        )
        return ConversationHandler.END

    borrador = {
        "fecha": extraido.get("fecha"),
        "destino": extraido.get("destino"),
        "monto": extraido.get("monto"),
        "balance": extraido.get("balance"),
        "moneda": extraido.get("moneda", "ARS"),
        "id_etiqueta": etiqueta["id"] if etiqueta else None,
        "etiqueta": etiqueta["nombre"] if etiqueta else None,
        "advertencias": extraido.get("advertencias", []),
    }
    _guardar_borrador(context, update, borrador)

    if etiqueta is None:
        await _mostrar_selector(update, context, borrador)
        return ESPERANDO_SELEC_ETIQUETA

    await _mostrar_confirmacion(update, context, borrador)
    return ESPERANDO_CONFIRMACION


async def seleccionar_etiqueta(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    borrador = context.user_data.get(DRAFT_KEY)
    if not borrador:
        await query.edit_message_text(
            "La sesión expiró. Enviá el comprobante de nuevo."
        )
        return ConversationHandler.END

    partes = query.data.split(":")
    if len(partes) < 3:
        return ESPERANDO_SELEC_ETIQUETA
    id_etiqueta = int(partes[2])
    etiqueta = db.obtener_etiqueta(id_etiqueta, _gestion(context).db_path)
    if etiqueta is None:
        await query.answer("Etiqueta no encontrada.", show_alert=True)
        return ESPERANDO_SELEC_ETIQUETA

    borrador["id_etiqueta"] = etiqueta["id"]
    borrador["etiqueta"] = etiqueta["nombre"]
    _guardar_borrador(context, update, borrador)
    await _mostrar_confirmacion(update, context, borrador, query=query)
    return ESPERANDO_CONFIRMACION


async def paginar_etiquetas(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    partes = query.data.split(":")
    pagina = int(partes[2]) if len(partes) >= 3 else 0
    etiquetas = _gestion(context).listar_etiquetas()
    await query.edit_message_reply_markup(
        reply_markup=ui.construir_teclado_etiquetas(etiquetas, "draft", pagina)
    )
    return ESPERANDO_SELEC_ETIQUETA


async def etiqueta_por_texto(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    borrador = context.user_data.get(DRAFT_KEY)
    if not borrador:
        return ConversationHandler.END

    gestion = _gestion(context)
    etiquetas = gestion.listar_etiquetas()
    nombres = [etiqueta["nombre"] for etiqueta in etiquetas]
    nombre = parsers.extraer_etiqueta_de_caption(
        update.effective_message.text or "", nombres
    )
    if nombre is None:
        await update.effective_message.reply_text(
            "No reconozco esa etiqueta. Usá los botones o /cancelar."
        )
        return ESPERANDO_SELEC_ETIQUETA

    etiqueta = next(e for e in etiquetas if e["nombre"] == nombre)
    borrador["id_etiqueta"] = etiqueta["id"]
    borrador["etiqueta"] = etiqueta["nombre"]
    _guardar_borrador(context, update, borrador)
    await _mostrar_confirmacion(update, context, borrador)
    return ESPERANDO_CONFIRMACION


async def callback_confirmacion(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    borrador = context.user_data.get(DRAFT_KEY)
    if not borrador:
        await query.answer("La sesión expiró.", show_alert=True)
        return ConversationHandler.END

    accion = query.data.split(":")[1]

    if accion == "monto":
        await query.answer()
        await query.edit_message_text(
            "✏️ Enviá el nuevo monto (ej: 15000 o 15.000,50)."
        )
        return CORRIGIENDO_MONTO

    if accion == "fecha":
        await query.answer()
        await query.edit_message_text(
            "📅 Enviá la nueva fecha (ej: 15.11.26 o 2026-11-15)."
        )
        return CORRIGIENDO_FECHA

    if accion == "destino":
        await query.answer()
        await query.edit_message_text(
            "📝 Enviá el nuevo destino. Podés enviar '-' para dejarlo vacío."
        )
        return CORRIGIENDO_DESTINO

    if accion == "etiqueta":
        await query.answer()
        await _mostrar_selector(update, context, borrador, query=query)
        return ESPERANDO_SELEC_ETIQUETA

    if accion == "balance":
        actual = borrador.get("balance")
        borrador["balance"] = (
            "EGRESO" if actual in (None, "INGRESO") else "INGRESO"
        )
        _guardar_borrador(context, update, borrador)
        await query.answer("Balance actualizado.")
        await _mostrar_confirmacion(update, context, borrador, query=query)
        return ESPERANDO_CONFIRMACION

    if accion == "confirmar":
        faltantes = _faltantes(borrador)
        if faltantes:
            await query.answer(
                "Faltan datos: " + ", ".join(faltantes), show_alert=True
            )
            return ESPERANDO_CONFIRMACION

        try:
            resultado = _gestion(context).registrar_comprobante(
                monto=borrador["monto"],
                balance=borrador["balance"],
                id_etiqueta=borrador["id_etiqueta"],
                fecha=borrador["fecha"],
                destino=borrador.get("destino"),
            )
        except ErrorGestion as exc:
            await query.answer(str(exc), show_alert=True)
            return ESPERANDO_CONFIRMACION

        comprobante = resultado["comprobante"]
        await query.answer("Guardado.")
        await query.edit_message_text(
            f"✅ Guardado\n{ui.formatear_comprobante(comprobante)}"
        )
        await _enviar_avisos(update, resultado["avisos"])
        _limpiar_borrador(context, update)
        return ConversationHandler.END

    if accion == "cancelar":
        await query.answer()
        await query.edit_message_text("❌ Operación cancelada.")
        _limpiar_borrador(context, update)
        return ConversationHandler.END

    await query.answer()
    return ESPERANDO_CONFIRMACION


async def corregir_monto(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    borrador = context.user_data.get(DRAFT_KEY)
    if not borrador:
        return ConversationHandler.END
    try:
        monto = parsers.parsear_monto(update.effective_message.text or "")
    except ErrorParseo as exc:
        await update.effective_message.reply_text(
            f"⚠️ {exc}\nEnviá un monto válido o /cancelar."
        )
        return CORRIGIENDO_MONTO

    borrador["monto"] = monto
    _guardar_borrador(context, update, borrador)
    await _mostrar_confirmacion(update, context, borrador)
    return ESPERANDO_CONFIRMACION


async def corregir_fecha(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    borrador = context.user_data.get(DRAFT_KEY)
    if not borrador:
        return ConversationHandler.END
    try:
        fecha = parsers.parsear_fecha(update.effective_message.text or "")
    except ErrorParseo as exc:
        await update.effective_message.reply_text(
            f"⚠️ {exc}\nEnviá una fecha válida o /cancelar."
        )
        return CORRIGIENDO_FECHA

    borrador["fecha"] = fecha
    _guardar_borrador(context, update, borrador)
    await _mostrar_confirmacion(update, context, borrador)
    return ESPERANDO_CONFIRMACION


async def corregir_destino(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    borrador = context.user_data.get(DRAFT_KEY)
    if not borrador:
        return ConversationHandler.END
    texto = (update.effective_message.text or "").strip()
    borrador["destino"] = None if texto in {"", "-"} else texto[:200]
    _guardar_borrador(context, update, borrador)
    await _mostrar_confirmacion(update, context, borrador)
    return ESPERANDO_CONFIRMACION


async def recordatorio_confirmacion(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.effective_message.reply_text(
        "Usá los botones para editar o confirmar, o /cancelar para salir."
    )
    return ESPERANDO_CONFIRMACION


async def comprobante_pendiente(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.effective_message.reply_text(
        "Ya hay un comprobante en curso. Confirmá, editá o usá /cancelar."
    )
    return None


async def cancelar_conversacion(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    _limpiar_borrador(context, update)
    await update.effective_message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END


async def sesion_expirada(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data.pop(DRAFT_KEY, None)
    chat_id = (
        update.effective_chat.id
        if update and update.effective_chat
        else config.TELEGRAM_CHAT_ID
    )
    if chat_id:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "⏳ La sesión anterior expiró. "
                    "Enviá el comprobante de nuevo."
                ),
            )
        except Exception:  # pragma: no cover - defensivo
            logger.warning("No se pudo notificar la sesión expirada")
    return ConversationHandler.END


def obtener_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(FILTRO_ARCHIVO, recibir_comprobante),
        ],
        states={
            ESPERANDO_SELEC_ETIQUETA: [
                CallbackQueryHandler(
                    seleccionar_etiqueta, pattern=r"^draft:sel:"
                ),
                CallbackQueryHandler(
                    paginar_etiquetas, pattern=r"^draft:pag:"
                ),
                CallbackQueryHandler(
                    callback_confirmacion, pattern=r"^draft:cancelar$"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, etiqueta_por_texto
                ),
                MessageHandler(FILTRO_ARCHIVO, comprobante_pendiente),
            ],
            ESPERANDO_CONFIRMACION: [
                CallbackQueryHandler(
                    callback_confirmacion, pattern=r"^draft:"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    recordatorio_confirmacion,
                ),
                MessageHandler(FILTRO_ARCHIVO, comprobante_pendiente),
            ],
            CORRIGIENDO_MONTO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, corregir_monto
                ),
                MessageHandler(FILTRO_ARCHIVO, comprobante_pendiente),
            ],
            CORRIGIENDO_FECHA: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, corregir_fecha
                ),
                MessageHandler(FILTRO_ARCHIVO, comprobante_pendiente),
            ],
            CORRIGIENDO_DESTINO: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, corregir_destino
                ),
                MessageHandler(FILTRO_ARCHIVO, comprobante_pendiente),
            ],
            ConversationHandler.TIMEOUT: [
                TypeHandler(Update, sesion_expirada),
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar_conversacion),
            MessageHandler(
                filters.Regex(r"^/?cancelar$"), cancelar_conversacion
            ),
        ],
        name="comprobante",
        persistent=True,
        conversation_timeout=3600,
    )
