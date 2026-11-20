"""Utilidades de presentación para Telegram."""

from __future__ import annotations

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from utils.formato import formatear_fecha, formatear_monto

TEXTO_BIENVENIDA = (
    "👋 Hola. Soy GestionGastos, tu registro personal de gastos e ingresos.\n\n"
    "Podés enviarme una foto o un PDF de un comprobante y yo extraigo los datos. "
    "También podés usar comandos de texto.\n\n"
    "Escribí /ayuda para ver la guía completa."
)

TEXTO_AYUDA = """📖 Guía rápida de GestionGastos

🧾 COMPROBANTES
• Enviá una foto o PDF, con o sin la etiqueta en el texto.
• El bot extrae fecha, monto y balance; vos confirmás o corregís.
• Ejemplo: enviar una foto con el texto "nafta".

✍️ BALANCES MANUALES
• + etiqueta monto → ingreso. Ej: + cuota 850000
• - etiqueta monto → egreso. Ej: - nafta 15000

📊 ANÁLISIS
• analisis → mes actual (desde la última cuota)
• analisis 01.11.26 → desde esa fecha hasta hoy
• analisis 01.11.26 15.11.26 → rango cerrado

🚨 ALERTAS
• alerta etiqueta monto → Ej: alerta nafta 15000
• alerta monto → Ej: alerta 100000
• alertas → ver alertas activas

🏷️ ETIQUETAS
• etiqueta nombre → crear
• etiquetas → listar
• eliminar etiqueta nombre → borrar si no tiene comprobantes

✏️ EDICIÓN
• editar → elegir de los últimos 10
• editar 42 → abrir el comprobante #42
• borrar → elegir de los últimos 10
• borrar 42 → borrar el comprobante #42

⚙️ SISTEMA
• /cancelar → cancelar la operación en curso
• /ayuda o /comandos → esta guía

Los comandos funcionan con o sin barra inicial."""


def construir_teclado_etiquetas(
    etiquetas: list[dict[str, Any]],
    prefijo: str,
    pagina: int = 0,
    por_pagina: int = 8,
) -> InlineKeyboardMarkup:
    total = len(etiquetas)
    total_paginas = max((total + por_pagina - 1) // por_pagina, 1)
    pagina = max(0, min(int(pagina), total_paginas - 1))
    inicio = pagina * por_pagina
    seleccion = etiquetas[inicio : inicio + por_pagina]

    filas: list[list[InlineKeyboardButton]] = []
    fila: list[InlineKeyboardButton] = []
    for etiqueta in seleccion:
        fila.append(
            InlineKeyboardButton(
                etiqueta["nombre"],
                callback_data=f"{prefijo}:sel:{etiqueta['id']}",
            )
        )
        if len(fila) == 2:
            filas.append(fila)
            fila = []
    if fila:
        filas.append(fila)

    navegacion: list[InlineKeyboardButton] = []
    if pagina > 0:
        navegacion.append(
            InlineKeyboardButton(
                "◀️", callback_data=f"{prefijo}:pag:{pagina - 1}"
            )
        )
    if pagina < total_paginas - 1:
        navegacion.append(
            InlineKeyboardButton(
                "▶️", callback_data=f"{prefijo}:pag:{pagina + 1}"
            )
        )
    if navegacion:
        filas.append(navegacion)

    filas.append(
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"{prefijo}:cancelar")]
    )
    return InlineKeyboardMarkup(filas)


def construir_teclado_confirmacion() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Monto", callback_data="draft:monto"),
                InlineKeyboardButton(
                    "🏷️ Etiqueta", callback_data="draft:etiqueta"
                ),
            ],
            [
                InlineKeyboardButton("📅 Fecha", callback_data="draft:fecha"),
                InlineKeyboardButton(
                    "🔄 Balance", callback_data="draft:balance"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📝 Destino", callback_data="draft:destino"
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Confirmar", callback_data="draft:confirmar"
                ),
                InlineKeyboardButton(
                    "❌ Cancelar", callback_data="draft:cancelar"
                ),
            ],
        ]
    )


def construir_teclado_edicion(id_comprobante: int) -> InlineKeyboardMarkup:
    prefijo = f"edit:{id_comprobante}"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Monto", callback_data=f"{prefijo}:monto"),
                InlineKeyboardButton(
                    "🏷️ Etiqueta", callback_data=f"{prefijo}:etiqueta"
                ),
            ],
            [
                InlineKeyboardButton("📅 Fecha", callback_data=f"{prefijo}:fecha"),
                InlineKeyboardButton(
                    "🔄 Balance", callback_data=f"{prefijo}:balance"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📝 Destino", callback_data=f"{prefijo}:destino"
                )
            ],
            [
                InlineKeyboardButton("✅ Listo", callback_data=f"{prefijo}:listo"),
                InlineKeyboardButton(
                    "❌ Cancelar", callback_data=f"{prefijo}:cancelar"
                ),
            ],
        ]
    )


def construir_teclado_borrado(id_comprobante: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑️ Sí, borrar", callback_data=f"borrar:si:{id_comprobante}"
                ),
                InlineKeyboardButton(
                    "❌ Cancelar", callback_data=f"borrar:no:{id_comprobante}"
                ),
            ]
        ]
    )


def construir_teclado_seleccion(
    comprobantes: list[dict[str, Any]], accion: str
) -> InlineKeyboardMarkup:
    filas: list[list[InlineKeyboardButton]] = []
    for comprobante in comprobantes:
        texto = (
            f"#{comprobante['id']} · {formatear_fecha(comprobante['fecha'])} · "
            f"{formatear_monto(comprobante['monto'])} · "
            f"{comprobante['etiqueta']}"
        )
        filas.append(
            [
                InlineKeyboardButton(
                    texto,
                    callback_data=f"sel:{accion}:{comprobante['id']}",
                )
            ]
        )
    filas.append(
        [InlineKeyboardButton("❌ Cancelar", callback_data="sel:cancelar:0")]
    )
    return InlineKeyboardMarkup(filas)


def construir_teclado_confirmar_eliminar(
    id_etiqueta: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑️ Sí, eliminar", callback_data=f"del_ok:{id_etiqueta}"
                ),
                InlineKeyboardButton(
                    "❌ Cancelar", callback_data=f"del_no:{id_etiqueta}"
                ),
            ]
        ]
    )


def formatear_borrador(borrador: dict[str, Any]) -> str:
    fecha = (
        formatear_fecha(borrador["fecha"])
        if borrador.get("fecha")
        else "⚠️ sin detectar"
    )
    monto = (
        formatear_monto(borrador["monto"])
        if borrador.get("monto") is not None
        else "⚠️ sin detectar"
    )
    balance = {
        "INGRESO": "Ingreso",
        "EGRESO": "Egreso",
    }.get(borrador.get("balance"), "⚠️ sin determinar")
    etiqueta = borrador.get("etiqueta") or "⚠️ sin etiqueta"
    destino = borrador.get("destino") or "—"

    lineas = [
        "📎 Comprobante recibido",
        "",
        f"📅 Fecha: {fecha}",
        f"💰 Monto: {monto}",
        f"🔄 Balance: {balance}",
        f"🏷️ Etiqueta: {etiqueta}",
        f"📝 Destino: {destino}",
    ]
    incompleto = (
        borrador.get("fecha") is None
        or borrador.get("monto") is None
        or borrador.get("balance") is None
        or borrador.get("id_etiqueta") is None
    )
    if incompleto:
        lineas.extend(["", "⚠️ Completá los campos marcados antes de confirmar."])
    return "\n".join(lineas)


def formatear_comprobante(comprobante: dict[str, Any]) -> str:
    balance = (
        "Ingreso" if comprobante["balance"] == "INGRESO" else "Egreso"
    )
    texto = (
        f"#{comprobante['id']} · {formatear_fecha(comprobante['fecha'])} · "
        f"{formatear_monto(comprobante['monto'])} · {balance} · "
        f"{comprobante['etiqueta']}"
    )
    if comprobante.get("destino"):
        texto += f" · {comprobante['destino']}"
    return texto


def formatear_alerta(aviso: dict[str, Any]) -> str:
    if aviso["tipo"] == "ETIQUETA":
        texto = (
            f"🏷️ {aviso.get('etiqueta')}: "
            f"{formatear_monto(aviso['monto_limite'])}"
        )
    else:
        texto = f"💸 Gasto total: {formatear_monto(aviso['monto_limite'])}"
    if not aviso.get("activo", 1):
        texto += " (inactiva)"
    return texto


def dividir_texto(texto: str, limite: int = 4000) -> list[str]:
    if len(texto) <= limite:
        return [texto]

    partes: list[str] = []
    actual: list[str] = []
    longitud = 0
    for linea in texto.splitlines():
        if longitud + len(linea) + 1 > limite and actual:
            partes.append("\n".join(actual))
            actual = [linea]
            longitud = len(linea) + 1
        else:
            actual.append(linea)
            longitud += len(linea) + 1
    if actual:
        partes.append("\n".join(actual))
    return partes


async def enviar_texto(update: Update, texto: str) -> None:
    for parte in dividir_texto(texto):
        await update.effective_message.reply_text(parte)
