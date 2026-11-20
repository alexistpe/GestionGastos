from datetime import date

import pytest

from database import db
from modules.gestion import ErrorGestion, Gestion


def id_etiqueta(db_path, nombre):
    etiqueta = db.obtener_etiqueta_por_nombre(nombre, db_path)
    assert etiqueta is not None, f"Falta la etiqueta {nombre}"
    return etiqueta["id"]


def test_registrar_comprobante_por_nombre_y_por_id(db_path):
    gestion = Gestion(db_path)

    resultado = gestion.registrar_comprobante(
        monto="15.000",
        balance="egreso",
        etiqueta="Nafta",
        fecha="15.11.26",
        destino="YPF",
    )
    comprobante = resultado["comprobante"]
    assert comprobante["etiqueta"] == "nafta"
    assert comprobante["monto"] == 15000
    assert comprobante["balance"] == "EGRESO"
    assert comprobante["fecha"] == "2026-11-15"
    assert comprobante["destino"] == "YPF"

    gym_id = id_etiqueta(db_path, "gym")
    segundo = gestion.registrar_comprobante(
        monto=5000,
        balance="INGRESO",
        id_etiqueta=gym_id,
        fecha=date(2026, 11, 16),
    )
    assert segundo["comprobante"]["etiqueta"] == "gym"
    assert segundo["comprobante"]["balance"] == "INGRESO"
    assert segundo["comprobante"]["fecha"] == "2026-11-16"


def test_registrar_comprobante_validaciones(db_path):
    gestion = Gestion(db_path)

    with pytest.raises(ErrorGestion):
        gestion.registrar_comprobante(1000, "EGRESO", etiqueta="noexiste")
    with pytest.raises(ErrorGestion):
        gestion.registrar_comprobante(1000, "OTRO", etiqueta="nafta")
    with pytest.raises(ErrorGestion):
        gestion.registrar_comprobante(0, "EGRESO", etiqueta="nafta")
    with pytest.raises(ErrorGestion):
        gestion.registrar_comprobante(-5, "EGRESO", etiqueta="nafta")
    with pytest.raises(ErrorGestion):
        gestion.registrar_comprobante(
            1000, "EGRESO", etiqueta="nafta", id_etiqueta=1
        )
    with pytest.raises(ErrorGestion):
        gestion.registrar_comprobante(
            1000, "EGRESO", etiqueta="nafta", fecha="31.02.26"
        )


def test_gestionar_etiquetas(db_path):
    gestion = Gestion(db_path)

    creada = gestion.crear_etiqueta("Tarjeta Crédito")
    assert creada["nombre"] == "tarjeta_credito"

    with pytest.raises(ErrorGestion):
        gestion.crear_etiqueta("tarjeta credito")

    assert gestion.eliminar_etiqueta("Tarjeta Crédito") == "tarjeta_credito"
    with pytest.raises(ErrorGestion):
        gestion.eliminar_etiqueta("tarjeta_credito")

    gestion.crear_etiqueta("temporal")
    gestion.registrar_comprobante(1000, "EGRESO", etiqueta="temporal")
    with pytest.raises(ErrorGestion):
        gestion.eliminar_etiqueta("temporal")


def test_configurar_alertas(db_path):
    gestion = Gestion(db_path)

    aviso = gestion.configurar_alerta_etiqueta("Nafta", "15.000")
    assert aviso["tipo"] == "ETIQUETA"
    assert aviso["etiqueta"] == "nafta"
    assert aviso["monto_limite"] == 15000

    actualizado = gestion.configurar_alerta_etiqueta("nafta", "20.000")
    assert actualizado["id"] == aviso["id"]
    assert actualizado["monto_limite"] == 20000

    total = gestion.configurar_alerta_total("100.000")
    assert total["tipo"] == "MONTO_TOTAL"
    assert total["monto_limite"] == 100000

    assert len(gestion.listar_alertas()) == 2
    with pytest.raises(ErrorGestion):
        gestion.configurar_alerta_etiqueta("noexiste", 1000)


def test_registro_dispara_alerta_y_no_duplica(db_path):
    gestion = Gestion(db_path)
    hoy = date.today()
    inicio = hoy.replace(day=1)

    gestion.registrar_comprobante(
        100000, "INGRESO", etiqueta="cuota", fecha=inicio
    )
    aviso = gestion.configurar_alerta_etiqueta("nafta", 10000)

    primero = gestion.registrar_comprobante(
        15000, "EGRESO", etiqueta="nafta", fecha=hoy
    )
    clave = f"ETIQUETA:{aviso['id']}"
    assert clave in [alerta["clave"] for alerta in primero["avisos"]]

    segundo = gestion.registrar_comprobante(
        5000, "EGRESO", etiqueta="nafta", fecha=hoy
    )
    assert segundo["avisos"] == []


def test_actualizar_y_eliminar_comprobante(db_path):
    gestion = Gestion(db_path)
    resultado = gestion.registrar_comprobante(
        15000,
        "EGRESO",
        etiqueta="nafta",
        fecha="2026-11-10",
        destino="YPF",
    )
    id_comprobante = resultado["comprobante"]["id"]

    actualizado = gestion.actualizar_comprobante(
        id_comprobante,
        {
            "monto": "20.000",
            "etiqueta": "Gym",
            "balance": "ingreso",
            "fecha": "11.11.26",
            "destino": "Cuota",
        },
    )
    comprobante = actualizado["comprobante"]
    assert comprobante["monto"] == 20000
    assert comprobante["etiqueta"] == "gym"
    assert comprobante["balance"] == "INGRESO"
    assert comprobante["fecha"] == "2026-11-11"
    assert comprobante["destino"] == "Cuota"

    with pytest.raises(ErrorGestion):
        gestion.actualizar_comprobante(9999, {"monto": 100})
    with pytest.raises(ErrorGestion):
        gestion.actualizar_comprobante(id_comprobante, {})

    assert gestion.eliminar_comprobante(id_comprobante) is True
    with pytest.raises(ErrorGestion):
        gestion.eliminar_comprobante(id_comprobante)


def test_generar_resumen_y_periodo(db_path):
    gestion = Gestion(db_path)
    hoy = date(2026, 11, 20)

    gestion.registrar_comprobante(
        850000, "INGRESO", etiqueta="cuota", fecha="2026-11-03"
    )
    gestion.registrar_comprobante(
        15000, "EGRESO", etiqueta="nafta", fecha="2026-11-10"
    )

    resumen = gestion.generar_resumen("MENSUAL", hoy=hoy)
    assert resumen.monto_neto == 835000

    inicio, fin = gestion.periodo_actual(hoy)
    assert inicio == date(2026, 11, 3)
    assert fin == hoy

    rango = gestion.generar_resumen(
        "RANGO", desde="01.11.26", hasta="20.11.26"
    )
    assert rango.monto_saliente == 15000

    with pytest.raises(ErrorGestion):
        gestion.generar_resumen("RANGO", desde="01.11.26")
    with pytest.raises(ErrorGestion):
        gestion.generar_resumen(
            "RANGO", desde="20.11.26", hasta="01.11.26"
        )
    with pytest.raises(ErrorGestion):
        gestion.generar_resumen("OTRO")


def test_conocer_etiqueta(db_path):
    gestion = Gestion(db_path)

    assert gestion.conocer_etiqueta("Nafta")["nombre"] == "nafta"
    assert gestion.conocer_etiqueta("noexiste") is None
    with pytest.raises(ErrorGestion):
        gestion.conocer_etiqueta("!!!")
