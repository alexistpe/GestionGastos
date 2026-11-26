from datetime import date

import pytest

from database import db
from modules.gestion import ErrorGestion, Gestion


def id_etiqueta(db_path, nombre):
    etiqueta = db.obtener_etiqueta_por_nombre(nombre, db_path)
    assert etiqueta is not None, f"Falta la etiqueta {nombre}"
    return etiqueta["id"]


def crear(
    db_path,
    nombre,
    monto,
    balance="EGRESO",
    fecha="2026-11-10",
    destino=None,
):
    return db.crear_comprobante(
        fecha=fecha,
        monto=monto,
        balance=balance,
        id_etiqueta=id_etiqueta(db_path, nombre),
        destino=destino,
        db_path=db_path,
    )


def test_resumen_mensual_totales_y_ahorro(db_path):
    db.crear_etiqueta("supermercado", db_path=db_path)
    crear(db_path, "cuota", 850000, "INGRESO", "2026-11-03")
    crear(db_path, "nafta", 15000, fecha="2026-11-10")
    crear(db_path, "gym", 20000, fecha="2026-11-05")
    crear(db_path, "supermercado", 30000, fecha="2026-11-12")
    crear(db_path, "ahorro", 100000, fecha="2026-11-15")
    crear(db_path, "ahorro", 20000, "INGRESO", "2026-11-18")

    gestion = Gestion(db_path)
    resumen = gestion.generar_resumen("MENSUAL", hoy=date(2026, 11, 20))

    assert resumen.tipo.value == "MENSUAL"
    assert resumen.desde == date(2026, 11, 3)
    assert resumen.hasta == date(2026, 11, 20)
    assert resumen.monto_ingresado == pytest.approx(870000)
    assert resumen.monto_saliente == pytest.approx(165000)
    assert resumen.monto_neto == pytest.approx(705000)
    assert resumen.ahorro_inicial == 0
    assert resumen.ahorro_depositado == pytest.approx(100000)
    assert resumen.ahorro_extraido == pytest.approx(20000)
    assert resumen.monto_ahorro == pytest.approx(80000)
    assert resumen.ahorro_acumulado == pytest.approx(80000)

    assert [(item["etiqueta"], item["monto"]) for item in resumen.gastos_por_etiqueta] == [
        ("ahorro", 100000),
        ("supermercado", 30000),
        ("gym", 20000),
        ("nafta", 15000),
    ]
    assert [item["etiqueta"] for item in resumen.ingresos] == ["cuota", "ahorro"]

    rutina = {item["etiqueta"]: item for item in resumen.rutina}
    assert set(rutina) == {"gym", "peluqueria", "nafta", "seguro", "claro"}
    assert rutina["gym"]["gastado"] == pytest.approx(20000)
    assert rutina["gym"]["completado"] is True
    assert rutina["nafta"]["gastado"] == pytest.approx(15000)
    assert rutina["peluqueria"]["completado"] is False
    assert resumen.monto_gastado_rutina == pytest.approx(35000)
    assert resumen.monto_pendiente_rutina is None
    assert resumen.rutina_completa is False

    assert resumen.gastos_no_esenciales == [
        {"etiqueta": "supermercado", "monto": 30000}
    ]
    assert resumen.monto_gastos_no_esenciales == pytest.approx(30000)

    datos = resumen.a_dict()
    assert datos["monto_neto"] == pytest.approx(705000)
    assert datos["desde"] == "2026-11-03"
    assert datos["hasta"] == "2026-11-20"

    texto = resumen.a_texto()
    assert "Análisis del mes" in texto
    assert "Rutina" in texto
    assert "Gastos no esenciales" in texto
    assert "$705.000,00" in texto
    assert "$80.000,00" in texto
    assert "Saldo inicial" in texto
    assert "Depositado" in texto
    assert "Extraído" in texto
    assert "Neto del período" in texto
    assert "Saldo al cierre" in texto


def test_ahorro_inicial_y_acumulado(db_path):
    crear(db_path, "ahorro", 50000, "EGRESO", "2026-10-01")
    crear(db_path, "cuota", 850000, "INGRESO", "2026-11-03")
    crear(db_path, "ahorro", 100000, "EGRESO", "2026-11-15")
    crear(db_path, "ahorro", 20000, "INGRESO", "2026-11-18")

    gestion = Gestion(db_path)
    gestion.configurar_saldo_inicial_ahorro(30000)

    resumen = gestion.generar_resumen("MENSUAL", hoy=date(2026, 11, 20))

    assert resumen.ahorro_inicial == pytest.approx(80000)
    assert resumen.ahorro_depositado == pytest.approx(100000)
    assert resumen.ahorro_extraido == pytest.approx(20000)
    assert resumen.monto_ahorro == pytest.approx(80000)
    assert resumen.ahorro_acumulado == pytest.approx(160000)

    datos = resumen.a_dict()
    assert datos["ahorro_inicial"] == pytest.approx(80000)
    assert datos["ahorro_acumulado"] == pytest.approx(160000)

    rango = gestion.generar_resumen(
        "RANGO", desde="01.11.26", hasta="30.11.26"
    )
    assert rango.ahorro_inicial == pytest.approx(80000)
    assert rango.ahorro_acumulado == pytest.approx(160000)


def test_ahorro_neto_negativo_y_advertencia(db_path):
    crear(db_path, "cuota", 850000, "INGRESO", "2026-11-03")
    crear(db_path, "ahorro", 100000, "EGRESO", "2026-11-15")
    crear(db_path, "ahorro", 150000, "INGRESO", "2026-11-18")

    gestion = Gestion(db_path)
    gestion.configurar_saldo_inicial_ahorro(50000)

    resumen = gestion.generar_resumen("MENSUAL", hoy=date(2026, 11, 20))

    assert resumen.monto_ahorro == pytest.approx(-50000)
    assert resumen.ahorro_acumulado == 0
    texto = resumen.a_texto_ahorro()
    assert "balance de ahorro del período es negativo" in texto
    assert "saldo acumulado de ahorro es negativo" not in texto


def test_rutina_con_presupuestos(db_path):
    crear(db_path, "cuota", 850000, "INGRESO", "2026-11-03")
    crear(db_path, "gym", 20000, fecha="2026-11-05")
    crear(db_path, "nafta", 15000, fecha="2026-11-10")

    gestion = Gestion(db_path)
    gestion.configurar_alerta_etiqueta("gym", "25.000")
    gestion.configurar_alerta_etiqueta("nafta", "20.000")

    resumen = gestion.generar_resumen("MENSUAL", hoy=date(2026, 11, 20))
    rutina = {item["etiqueta"]: item for item in resumen.rutina}

    assert rutina["gym"]["presupuesto"] == pytest.approx(25000)
    assert rutina["gym"]["pendiente"] == pytest.approx(5000)
    assert rutina["nafta"]["presupuesto"] == pytest.approx(20000)
    assert rutina["nafta"]["pendiente"] == pytest.approx(5000)
    assert rutina["seguro"]["presupuesto"] is None
    assert rutina["seguro"]["pendiente"] is None
    assert resumen.monto_pendiente_rutina == pytest.approx(10000)
    assert resumen.rutina_completa is False

    crear(db_path, "peluqueria", 10000, fecha="2026-11-14")
    crear(db_path, "seguro", 5000, fecha="2026-11-15")
    crear(db_path, "claro", 8000, fecha="2026-11-16")

    completo = gestion.generar_resumen("MENSUAL", hoy=date(2026, 11, 20))
    assert completo.rutina_completa is True
    assert completo.monto_pendiente_rutina == pytest.approx(10000)
    assert completo.monto_gastado_rutina == pytest.approx(58000)


def test_resumen_por_rango(db_path):
    db.crear_etiqueta("supermercado", db_path=db_path)
    crear(db_path, "cuota", 800000, "INGRESO", "2026-10-01")
    crear(db_path, "nafta", 10000, fecha="2026-10-10")
    crear(db_path, "supermercado", 20000, fecha="2026-11-05")
    crear(db_path, "gym", 30000, fecha="2026-11-10")

    gestion = Gestion(db_path)
    resumen = gestion.generar_resumen(
        "RANGO", desde="01.11.26", hasta="15.11.26"
    )

    assert resumen.tipo.value == "RANGO"
    assert resumen.desde == date(2026, 11, 1)
    assert resumen.hasta == date(2026, 11, 15)
    assert resumen.monto_ingresado == pytest.approx(0)
    assert resumen.monto_saliente == pytest.approx(50000)
    assert resumen.monto_neto == pytest.approx(-50000)
    assert [(item["etiqueta"], item["monto"]) for item in resumen.gastos_por_etiqueta] == [
        ("gym", 30000),
        ("supermercado", 20000),
    ]
    assert resumen.gastos_no_esenciales == [
        {"etiqueta": "supermercado", "monto": 20000}
    ]

    texto = resumen.a_texto()
    assert "Análisis por rango" in texto
    assert "Rutina" not in texto

    with pytest.raises(ErrorGestion):
        gestion.generar_resumen("RANGO", desde="01.11.26")
    with pytest.raises(ErrorGestion):
        gestion.generar_resumen(
            "RANGO", desde="15.11.26", hasta="01.11.26"
        )
    with pytest.raises(ErrorGestion):
        gestion.generar_resumen("OTRO")


def test_periodo_mensual_desde_ultima_cuota(db_path):
    crear(db_path, "cuota", 800000, "INGRESO", "2026-10-05")
    crear(db_path, "nafta", 10000, fecha="2026-10-10")
    crear(db_path, "cuota", 850000, "INGRESO", "2026-11-03")
    crear(db_path, "gym", 20000, fecha="2026-11-05")

    gestion = Gestion(db_path)
    resumen = gestion.generar_resumen("MENSUAL", hoy=date(2026, 11, 20))

    assert resumen.desde == date(2026, 11, 3)
    assert len(resumen.comprobantes) == 2
    assert resumen.monto_ingresado == pytest.approx(850000)
    assert resumen.monto_saliente == pytest.approx(20000)
    assert {item["etiqueta"] for item in resumen.comprobantes} == {
        "cuota",
        "gym",
    }


def test_resumen_vacio(db_path):
    gestion = Gestion(db_path)
    resumen = gestion.generar_resumen("MENSUAL", hoy=date(2026, 11, 20))

    assert resumen.desde == date(2026, 11, 1)
    assert resumen.monto_ingresado == 0
    assert resumen.monto_saliente == 0
    assert resumen.monto_neto == 0
    assert resumen.monto_ahorro == 0
    assert resumen.gastos_por_etiqueta == []
    assert resumen.ingresos == []
    assert len(resumen.rutina) == 5
    assert all(not item["completado"] for item in resumen.rutina)
    assert resumen.monto_gastado_rutina == 0
    assert resumen.monto_pendiente_rutina is None
    assert resumen.rutina_completa is False
    assert resumen.gastos_no_esenciales == []
    assert resumen.monto_gastos_no_esenciales == 0

    texto = resumen.a_texto()
    assert "Sin gastos registrados." in texto
    assert "Sin ingresos registrados." in texto
    assert "sin presupuesto definido" in texto
