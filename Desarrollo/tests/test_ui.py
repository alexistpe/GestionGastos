from datetime import date

from utils import telegram as ui


def callbacks(markup):
    return [
        boton.callback_data
        for fila in markup.inline_keyboard
        for boton in fila
    ]


def test_teclado_etiquetas_pagina_0():
    etiquetas = [
        {"id": i, "nombre": f"etiqueta{i}"} for i in range(1, 11)
    ]
    teclado = ui.construir_teclado_etiquetas(etiquetas, "draft", pagina=0)

    assert len(teclado.inline_keyboard) == 6
    datos = callbacks(teclado)
    assert "draft:sel:1" in datos
    assert "draft:sel:8" in datos
    assert "draft:pag:1" in datos
    assert "draft:cancelar" in datos
    assert "draft:pag:-1" not in datos


def test_teclado_etiquetas_pagina_1():
    etiquetas = [
        {"id": i, "nombre": f"etiqueta{i}"} for i in range(1, 11)
    ]
    teclado = ui.construir_teclado_etiquetas(etiquetas, "draft", pagina=1)

    datos = callbacks(teclado)
    assert "draft:sel:9" in datos
    assert "draft:sel:10" in datos
    assert "draft:pag:0" in datos
    assert "draft:cancelar" in datos


def test_teclado_confirmacion():
    teclado = ui.construir_teclado_confirmacion()
    datos = callbacks(teclado)

    assert "draft:monto" in datos
    assert "draft:etiqueta" in datos
    assert "draft:fecha" in datos
    assert "draft:balance" in datos
    assert "draft:destino" in datos
    assert "draft:confirmar" in datos
    assert "draft:cancelar" in datos


def test_teclado_edicion():
    teclado = ui.construir_teclado_edicion(42)
    datos = callbacks(teclado)

    assert "edit:42:monto" in datos
    assert "edit:42:etiqueta" in datos
    assert "edit:42:fecha" in datos
    assert "edit:42:balance" in datos
    assert "edit:42:destino" in datos
    assert "edit:42:listo" in datos
    assert "edit:42:cancelar" in datos


def test_teclado_borrado():
    teclado = ui.construir_teclado_borrado(7)
    assert callbacks(teclado) == ["borrar:si:7", "borrar:no:7"]


def test_teclado_seleccion():
    comprobantes = [
        {
            "id": 1,
            "fecha": "2026-11-15",
            "monto": 15000,
            "etiqueta": "nafta",
        }
    ]
    teclado = ui.construir_teclado_seleccion(comprobantes, "editar")
    datos = callbacks(teclado)

    assert "sel:editar:1" in datos
    assert "sel:cancelar:0" in datos


def test_teclado_confirmar_eliminar():
    teclado = ui.construir_teclado_confirmar_eliminar(3)
    assert callbacks(teclado) == ["del_ok:3", "del_no:3"]


def test_formatear_borrador_completo():
    borrador = {
        "fecha": "2026-11-15",
        "monto": 15000,
        "balance": "EGRESO",
        "etiqueta": "nafta",
        "id_etiqueta": 3,
        "destino": "YPF",
    }
    texto = ui.formatear_borrador(borrador)

    assert "15.11.26" in texto
    assert "$15.000,00" in texto
    assert "Egreso" in texto
    assert "nafta" in texto
    assert "YPF" in texto
    assert "⚠️ Completá" not in texto


def test_formatear_borrador_incompleto():
    borrador = {
        "fecha": None,
        "monto": None,
        "balance": None,
        "etiqueta": None,
        "id_etiqueta": None,
        "destino": None,
    }
    texto = ui.formatear_borrador(borrador)

    assert "⚠️ sin detectar" in texto
    assert "⚠️ sin determinar" in texto
    assert "⚠️ sin etiqueta" in texto
    assert "⚠️ Completá" in texto


def test_formatear_comprobante():
    comprobante = {
        "id": 42,
        "fecha": "2026-11-15",
        "monto": 15000,
        "balance": "EGRESO",
        "etiqueta": "nafta",
        "destino": "YPF",
    }
    texto = ui.formatear_comprobante(comprobante)

    assert texto.startswith("#42")
    assert "15.11.26" in texto
    assert "$15.000,00" in texto
    assert "Egreso" in texto
    assert "nafta" in texto
    assert "YPF" in texto


def test_formatear_alerta():
    assert (
        ui.formatear_alerta(
            {"tipo": "ETIQUETA", "etiqueta": "nafta", "monto_limite": 15000}
        )
        == "🏷️ nafta: $15.000,00"
    )
    assert (
        ui.formatear_alerta({"tipo": "MONTO_TOTAL", "monto_limite": 100000})
        == "💸 Gasto total: $100.000,00"
    )


def test_formatear_alerta_ahorro_y_id():
    aviso = {
        "id": 5,
        "tipo": "ETIQUETA",
        "etiqueta": "ahorro",
        "monto_limite": 50000,
        "activo": 1,
    }
    assert (
        ui.formatear_alerta(aviso)
        == "🏷️ ahorro (máx. extracciones): $50.000,00"
    )
    assert (
        ui.formatear_alerta(aviso, incluir_id=True)
        == "#5 · 🏷️ ahorro (máx. extracciones): $50.000,00"
    )


def test_teclados_alertas():
    avisos = [
        {
            "id": 1,
            "tipo": "ETIQUETA",
            "etiqueta": "nafta",
            "monto_limite": 15000,
            "activo": 1,
        },
        {
            "id": 2,
            "tipo": "MONTO_TOTAL",
            "monto_limite": 100000,
            "activo": 1,
        },
    ]
    teclado = ui.construir_teclado_alertas(avisos)
    datos = callbacks(teclado)
    assert "del_aviso:1" in datos
    assert "del_aviso:2" in datos
    assert "del_aviso:cancelar" in datos

    confirmacion = ui.construir_teclado_confirmar_eliminar_alerta(5)
    assert callbacks(confirmacion) == [
        "del_aviso_ok:5",
        "del_aviso_no:5",
    ]


def test_dividir_texto():
    assert ui.dividir_texto("hola", limite=10) == ["hola"]

    texto = "\n".join(f"linea {i}" for i in range(10))
    partes = ui.dividir_texto(texto, limite=20)
    assert len(partes) > 1
    assert all(len(parte) <= 20 for parte in partes)


def test_texto_ayuda_incluye_comandos():
    assert "analisis" in ui.TEXTO_AYUDA
    assert "alerta" in ui.TEXTO_AYUDA
    assert "editar" in ui.TEXTO_AYUDA
    assert "/cancelar" in ui.TEXTO_AYUDA
