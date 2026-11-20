from datetime import date

from modules.aviso import Aviso, evaluar_avisos
from modules.resumen import Resumen, TipoResumen

ETIQUETAS = [
    {"id": 1, "nombre": "gym", "es_rutina": 1},
    {"id": 2, "nombre": "peluqueria", "es_rutina": 1},
    {"id": 3, "nombre": "nafta", "es_rutina": 1},
    {"id": 4, "nombre": "seguro", "es_rutina": 1},
    {"id": 5, "nombre": "claro", "es_rutina": 1},
]


def comp(
    id_comprobante,
    etiqueta,
    monto,
    balance,
    fecha="2026-11-10",
    id_etiqueta=0,
):
    return {
        "id": id_comprobante,
        "fecha": fecha,
        "destino": None,
        "monto": monto,
        "balance": balance,
        "id_etiqueta": id_etiqueta,
        "etiqueta": etiqueta,
    }


def resumen(
    comprobantes,
    avisos=None,
    tipo=TipoResumen.MENSUAL,
    desde=date(2026, 11, 3),
    hasta=date(2026, 11, 20),
):
    return Resumen(
        comprobantes=comprobantes,
        etiquetas=ETIQUETAS,
        avisos=avisos or [],
        tipo=tipo,
        desde=desde,
        hasta=hasta,
    )


def test_alerta_etiqueta_y_deduplicacion(db_path):
    comprobantes = [
        comp(1, "cuota", 100000, "INGRESO"),
        comp(2, "nafta", 20000, "EGRESO"),
    ]
    avisos = [
        {
            "id": 10,
            "tipo": "ETIQUETA",
            "id_etiqueta": 3,
            "etiqueta": "nafta",
            "monto_limite": 15000,
            "activo": 1,
        }
    ]
    datos = resumen(comprobantes, avisos)

    alertas = evaluar_avisos(datos, db_path)

    assert [alerta["clave"] for alerta in alertas] == ["ETIQUETA:10"]
    assert alertas[0]["tipo"] == "aviso"
    assert "nafta" in alertas[0]["mensaje"]
    assert "$20.000,00" in alertas[0]["mensaje"]
    assert "$15.000,00" in alertas[0]["mensaje"]
    assert evaluar_avisos(datos, db_path) == []


def test_alerta_monto_total(db_path):
    comprobantes = [
        comp(1, "cuota", 100000, "INGRESO"),
        comp(2, "gym", 30000, "EGRESO"),
        comp(3, "nafta", 20000, "EGRESO"),
    ]
    avisos = [
        {
            "id": 20,
            "tipo": "MONTO_TOTAL",
            "id_etiqueta": None,
            "etiqueta": None,
            "monto_limite": 40000,
            "activo": 1,
        }
    ]

    alertas = evaluar_avisos(resumen(comprobantes, avisos), db_path)

    assert [alerta["clave"] for alerta in alertas] == ["MONTO_TOTAL"]
    assert "$50.000,00" in alertas[0]["mensaje"]
    assert "$40.000,00" in alertas[0]["mensaje"]


def test_alerta_balance_negativo(db_path):
    comprobantes = [
        comp(1, "cuota", 100000, "INGRESO"),
        comp(2, "nafta", 150000, "EGRESO"),
    ]

    alertas = evaluar_avisos(resumen(comprobantes), db_path)

    assert [alerta["clave"] for alerta in alertas] == ["BALANCE_NEGATIVO"]
    assert "-$50.000,00" in alertas[0]["mensaje"]


def test_alerta_rutina_completa(db_path):
    comprobantes = [comp(1, "cuota", 100000, "INGRESO")]
    for indice, etiqueta in enumerate(
        ["gym", "peluqueria", "nafta", "seguro", "claro"], start=2
    ):
        comprobantes.append(comp(indice, etiqueta, 1000, "EGRESO"))

    alertas = evaluar_avisos(resumen(comprobantes), db_path)

    assert [alerta["clave"] for alerta in alertas] == ["RUTINA"]
    assert "Rutina completa" in alertas[0]["mensaje"]

    rango = resumen(
        comprobantes,
        tipo=TipoResumen.RANGO,
        desde=date(2026, 11, 3),
        hasta=date(2026, 11, 20),
    )
    assert evaluar_avisos(rango, db_path) == []


def test_alerta_ahorro(db_path):
    comprobantes = [
        comp(1, "ahorro", 200000, "INGRESO"),
        comp(2, "nafta", 50000, "EGRESO"),
    ]

    alertas = evaluar_avisos(resumen(comprobantes), db_path)

    assert [alerta["clave"] for alerta in alertas] == ["AHORRO"]
    assert "$200.000,00" in alertas[0]["mensaje"]
    assert "$150.000,00" in alertas[0]["mensaje"]


def test_sin_extracciones_de_ahorro_no_alerta(db_path):
    comprobantes = [
        comp(1, "cuota", 100000, "INGRESO"),
        comp(2, "ahorro", 50000, "EGRESO"),
        comp(3, "nafta", 10000, "EGRESO"),
    ]

    assert evaluar_avisos(resumen(comprobantes), db_path) == []


def test_alerta_no_superada_ni_inactiva(db_path):
    comprobantes = [
        comp(1, "cuota", 100000, "INGRESO"),
        comp(2, "nafta", 10000, "EGRESO"),
    ]
    avisos = [
        {
            "id": 30,
            "tipo": "ETIQUETA",
            "id_etiqueta": 3,
            "etiqueta": "nafta",
            "monto_limite": 15000,
            "activo": 1,
        },
        {
            "id": 31,
            "tipo": "ETIQUETA",
            "id_etiqueta": 3,
            "etiqueta": "nafta",
            "monto_limite": 5000,
            "activo": 0,
        },
    ]

    assert evaluar_avisos(resumen(comprobantes, avisos), db_path) == []


def test_nueva_alerta_en_otro_periodo(db_path):
    comprobantes = [
        comp(1, "cuota", 100000, "INGRESO"),
        comp(2, "nafta", 20000, "EGRESO"),
    ]
    avisos = [
        {
            "id": 40,
            "tipo": "ETIQUETA",
            "id_etiqueta": 3,
            "etiqueta": "nafta",
            "monto_limite": 15000,
            "activo": 1,
        }
    ]

    primero = resumen(comprobantes, avisos, desde=date(2026, 11, 3))
    assert [a["clave"] for a in evaluar_avisos(primero, db_path)] == ["ETIQUETA:40"]
    assert evaluar_avisos(primero, db_path) == []

    segundo = resumen(
        comprobantes,
        avisos,
        desde=date(2026, 12, 3),
        hasta=date(2026, 12, 20),
    )
    assert [a["clave"] for a in evaluar_avisos(segundo, db_path)] == ["ETIQUETA:40"]


def test_aviso_desde_fila_y_clave():
    etiqueta = Aviso.desde_fila(
        {
            "id": 5,
            "tipo": "ETIQUETA",
            "monto_limite": 100,
            "id_etiqueta": 2,
            "etiqueta": "nafta",
            "activo": 1,
        }
    )
    assert etiqueta.clave() == "ETIQUETA:5"
    assert etiqueta.activo is True
    assert etiqueta.etiqueta == "nafta"

    total = Aviso.desde_fila(
        {"id": 6, "tipo": "MONTO_TOTAL", "monto_limite": 100, "activo": 0}
    )
    assert total.clave() == "MONTO_TOTAL"
    assert total.activo is False
