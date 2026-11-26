import sqlite3
from datetime import date

import pytest

from database import db


def id_etiqueta(db_path, nombre):
    etiqueta = db.obtener_etiqueta_por_nombre(nombre, db_path)
    assert etiqueta is not None, f"Falta la etiqueta {nombre}"
    return etiqueta["id"]


def test_init_db_es_idempotente(db_path):
    db.init_db(db_path)
    etiquetas = db.listar_etiquetas(db_path)

    assert len(etiquetas) == 7
    assert {etiqueta["nombre"] for etiqueta in etiquetas} == {
        "gym",
        "peluqueria",
        "nafta",
        "seguro",
        "claro",
        "cuota",
        "ahorro",
    }
    assert sum(etiqueta["es_rutina"] for etiqueta in etiquetas) == 5

    with db.conectar(db_path) as conn:
        tablas = {
            fila["name"]
            for fila in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {
        "etiquetas",
        "comprobantes",
        "avisos",
        "sesion_estado",
        "avisos_disparados",
        "configuracion",
    }.issubset(tablas)


def test_crear_y_obtener_etiqueta(db_path):
    nueva_id = db.crear_etiqueta("supermercado", db_path=db_path)

    etiqueta = db.obtener_etiqueta(nueva_id, db_path)
    assert etiqueta == {"id": nueva_id, "nombre": "supermercado", "es_rutina": 0}

    por_nombre = db.obtener_etiqueta_por_nombre("supermercado", db_path)
    assert por_nombre["id"] == nueva_id

    with pytest.raises(sqlite3.IntegrityError):
        db.crear_etiqueta("supermercado", db_path=db_path)


def test_eliminar_etiqueta(db_path):
    nueva_id = db.crear_etiqueta("temporal", db_path=db_path)

    assert db.eliminar_etiqueta(nueva_id, db_path) is True
    assert db.obtener_etiqueta(nueva_id, db_path) is None
    assert db.eliminar_etiqueta(nueva_id, db_path) is False


def test_eliminar_etiqueta_en_uso_falla(db_path):
    nafta_id = id_etiqueta(db_path, "nafta")
    db.crear_comprobante(
        fecha=date(2026, 11, 10),
        monto=15000,
        balance="EGRESO",
        id_etiqueta=nafta_id,
        db_path=db_path,
    )

    assert db.etiqueta_en_uso(nafta_id, db_path) is True
    with pytest.raises(sqlite3.IntegrityError):
        db.eliminar_etiqueta(nafta_id, db_path)


def test_crud_comprobante(db_path):
    nafta_id = id_etiqueta(db_path, "nafta")
    gym_id = id_etiqueta(db_path, "gym")

    comprobante_id = db.crear_comprobante(
        fecha=date(2026, 11, 10),
        monto=15000,
        balance="EGRESO",
        id_etiqueta=nafta_id,
        destino="YPF",
        db_path=db_path,
    )

    comprobante = db.obtener_comprobante(comprobante_id, db_path)
    assert comprobante["fecha"] == "2026-11-10"
    assert comprobante["monto"] == 15000
    assert comprobante["balance"] == "EGRESO"
    assert comprobante["etiqueta"] == "nafta"
    assert comprobante["destino"] == "YPF"

    assert db.actualizar_comprobante(
        comprobante_id,
        {
            "fecha": "2026-11-01",
            "monto": 16000.5,
            "balance": "INGRESO",
            "id_etiqueta": gym_id,
            "destino": "Cuota gym",
        },
        db_path,
    )

    actualizado = db.obtener_comprobante(comprobante_id, db_path)
    assert actualizado["fecha"] == "2026-11-01"
    assert actualizado["monto"] == 16000.5
    assert actualizado["balance"] == "INGRESO"
    assert actualizado["etiqueta"] == "gym"
    assert actualizado["destino"] == "Cuota gym"

    assert db.eliminar_comprobante(comprobante_id, db_path) is True
    assert db.obtener_comprobante(comprobante_id, db_path) is None
    assert db.eliminar_comprobante(comprobante_id, db_path) is False


def test_actualizar_comprobante_sin_campos_validos(db_path):
    nafta_id = id_etiqueta(db_path, "nafta")
    comprobante_id = db.crear_comprobante(
        fecha=date(2026, 11, 10),
        monto=15000,
        balance="EGRESO",
        id_etiqueta=nafta_id,
        db_path=db_path,
    )

    assert db.actualizar_comprobante(comprobante_id, {"inexistente": 1}, db_path) is False


def test_listar_comprobantes_orden_y_filtros(db_path):
    nafta_id = id_etiqueta(db_path, "nafta")
    fechas = ["2026-11-01", "2026-11-15", "2026-11-10"]
    ids = []
    for indice, fecha in enumerate(fechas):
        ids.append(
            db.crear_comprobante(
                fecha=fecha,
                monto=1000 + indice,
                balance="EGRESO",
                id_etiqueta=nafta_id,
                db_path=db_path,
            )
        )

    todos = db.listar_comprobantes(db_path)
    assert [fila["fecha"] for fila in todos] == [
        "2026-11-15",
        "2026-11-10",
        "2026-11-01",
    ]

    desde = db.listar_comprobantes(db_path, desde="2026-11-05")
    assert [fila["fecha"] for fila in desde] == ["2026-11-15", "2026-11-10"]

    hasta = db.listar_comprobantes(db_path, hasta="2026-11-10")
    assert [fila["fecha"] for fila in hasta] == ["2026-11-10", "2026-11-01"]

    rango = db.listar_comprobantes(
        db_path, desde="2026-11-05", hasta="2026-11-12"
    )
    assert [fila["fecha"] for fila in rango] == ["2026-11-10"]

    with pytest.raises(ValueError):
        db.listar_comprobantes(
            db_path, desde="2026-11-15", hasta="2026-11-01"
        )

    ultimos = db.ultimos_comprobantes(2, db_path)
    assert [fila["id"] for fila in ultimos] == [ids[1], ids[2]]


def test_periodo_actual(db_path):
    assert db.inicio_periodo_actual(date(2026, 11, 20), db_path) == "2026-11-01"

    cuota_id = id_etiqueta(db_path, "cuota")
    db.crear_comprobante(
        fecha="2026-10-05",
        monto=800000,
        balance="INGRESO",
        id_etiqueta=cuota_id,
        db_path=db_path,
    )
    db.crear_comprobante(
        fecha="2026-11-03",
        monto=850000,
        balance="INGRESO",
        id_etiqueta=cuota_id,
        db_path=db_path,
    )
    db.crear_comprobante(
        fecha="2026-11-10",
        monto=1000,
        balance="EGRESO",
        id_etiqueta=cuota_id,
        db_path=db_path,
    )
    db.crear_comprobante(
        fecha="2026-12-01",
        monto=900000,
        balance="INGRESO",
        id_etiqueta=cuota_id,
        db_path=db_path,
    )

    assert db.inicio_periodo_actual(date(2026, 11, 20), db_path) == "2026-11-03"
    assert db.inicio_periodo_actual(date(2026, 12, 5), db_path) == "2026-12-01"


def test_listar_comprobantes_periodo(db_path):
    cuota_id = id_etiqueta(db_path, "cuota")
    nafta_id = id_etiqueta(db_path, "nafta")

    db.crear_comprobante(
        fecha="2026-10-05",
        monto=800000,
        balance="INGRESO",
        id_etiqueta=cuota_id,
        db_path=db_path,
    )
    db.crear_comprobante(
        fecha="2026-11-03",
        monto=850000,
        balance="INGRESO",
        id_etiqueta=cuota_id,
        db_path=db_path,
    )
    db.crear_comprobante(
        fecha="2026-11-10",
        monto=15000,
        balance="EGRESO",
        id_etiqueta=nafta_id,
        db_path=db_path,
    )
    db.crear_comprobante(
        fecha="2026-11-20",
        monto=5000,
        balance="EGRESO",
        id_etiqueta=nafta_id,
        db_path=db_path,
    )

    periodo = db.listar_comprobantes_periodo(
        fin=date(2026, 11, 20), db_path=db_path
    )
    assert [fila["fecha"] for fila in periodo] == [
        "2026-11-20",
        "2026-11-10",
        "2026-11-03",
    ]

    explicito = db.listar_comprobantes_periodo(
        inicio="2026-11-10", fin="2026-11-20", db_path=db_path
    )
    assert [fila["fecha"] for fila in explicito] == ["2026-11-20", "2026-11-10"]


def test_avisos_upsert_y_listado(db_path):
    nafta_id = id_etiqueta(db_path, "nafta")

    aviso_id = db.crear_o_actualizar_aviso(
        "ETIQUETA", 15000, id_etiqueta=nafta_id, db_path=db_path
    )
    mismo_id = db.crear_o_actualizar_aviso(
        "ETIQUETA", 20000, id_etiqueta=nafta_id, db_path=db_path
    )
    assert mismo_id == aviso_id
    assert db.obtener_aviso(aviso_id, db_path)["monto_limite"] == 20000

    total_id = db.crear_o_actualizar_aviso(
        "MONTO_TOTAL", 100000, db_path=db_path
    )
    mismo_total = db.crear_o_actualizar_aviso(
        "MONTO_TOTAL", 120000, db_path=db_path
    )
    assert mismo_total == total_id
    assert db.obtener_aviso(total_id, db_path)["monto_limite"] == 120000

    avisos = db.listar_avisos(db_path=db_path)
    assert len(avisos) == 2
    assert {aviso["tipo"] for aviso in avisos} == {"ETIQUETA", "MONTO_TOTAL"}

    assert db.desactivar_aviso(total_id, db_path) is True
    activos = db.listar_avisos(db_path=db_path)
    assert len(activos) == 1
    assert activos[0]["id"] == aviso_id

    assert db.eliminar_aviso(aviso_id, db_path) is True
    assert db.obtener_aviso(aviso_id, db_path) is None


def test_validaciones_de_avisos(db_path):
    nafta_id = id_etiqueta(db_path, "nafta")

    with pytest.raises(ValueError):
        db.crear_o_actualizar_aviso("ETIQUETA", 100, db_path=db_path)
    with pytest.raises(ValueError):
        db.crear_o_actualizar_aviso(
            "MONTO_TOTAL", 100, id_etiqueta=nafta_id, db_path=db_path
        )
    with pytest.raises(ValueError):
        db.crear_o_actualizar_aviso("OTRO", 100, db_path=db_path)


def test_eliminar_etiqueta_elimina_sus_avisos(db_path):
    gym_id = id_etiqueta(db_path, "gym")
    aviso_id = db.crear_o_actualizar_aviso(
        "ETIQUETA", 20000, id_etiqueta=gym_id, db_path=db_path
    )

    assert db.eliminar_etiqueta(gym_id, db_path) is True
    assert db.obtener_aviso(aviso_id, db_path) is None


def test_configuracion_y_saldo_ahorro(db_path):
    assert db.obtener_saldo_inicial_ahorro(db_path) == 0

    db.guardar_saldo_inicial_ahorro(50000, db_path)
    assert db.obtener_saldo_inicial_ahorro(db_path) == 50000
    assert float(
        db.obtener_configuracion("saldo_inicial_ahorro", db_path)
    ) == 50000

    ahorro_id = id_etiqueta(db_path, "ahorro")
    db.crear_comprobante(
        "2026-10-01", 100000, "EGRESO", ahorro_id, db_path=db_path
    )
    db.crear_comprobante(
        "2026-10-15", 20000, "INGRESO", ahorro_id, db_path=db_path
    )
    db.crear_comprobante(
        "2026-11-05", 30000, "EGRESO", ahorro_id, db_path=db_path
    )
    db.crear_comprobante(
        "2026-11-10", 10000, "INGRESO", ahorro_id, db_path=db_path
    )

    assert db.saldo_ahorro_antes("2026-11-01", db_path) == 130000
    assert db.saldo_ahorro_hasta("2026-11-05", db_path) == 160000
    assert db.saldo_ahorro_hasta("2026-11-10", db_path) == 150000


def test_avisos_disparados(db_path):
    assert db.registrar_aviso_disparado("MONTO_TOTAL", "2026-11-03", db_path) is True
    assert db.registrar_aviso_disparado("MONTO_TOTAL", "2026-11-03", db_path) is False
    assert db.ya_disparado("MONTO_TOTAL", "2026-11-03", db_path) is True
    assert db.ya_disparado("MONTO_TOTAL", "2026-12-01", db_path) is False
    assert db.registrar_aviso_disparado("MONTO_TOTAL", "2026-12-01", db_path) is True
    assert db.limpiar_avisos_disparados("2026-11-03", db_path) == 1


def test_sesion_estado_crud(db_path):
    db.guardar_estado(
        chat_id=123,
        estado_actual="ESPERANDO_CONFIRMACION",
        contexto={"monto": 15000, "id_comprobante": None},
        db_path=db_path,
    )

    estado = db.obtener_estado(123, db_path)
    assert estado["estado_actual"] == "ESPERANDO_CONFIRMACION"
    assert estado["contexto"] == {"monto": 15000, "id_comprobante": None}
    assert estado["nombre_conversacion"] == "comprobante"

    db.guardar_estado(
        chat_id=123,
        estado_actual="CORRIGIENDO_MONTO",
        contexto={"monto": 16000},
        nombre_conversacion="edicion",
        db_path=db_path,
    )
    actualizado = db.obtener_estado(123, db_path)
    assert actualizado["estado_actual"] == "CORRIGIENDO_MONTO"
    assert actualizado["contexto"] == {"monto": 16000}
    assert actualizado["nombre_conversacion"] == "edicion"

    assert db.eliminar_estado(123, db_path) is True
    assert db.obtener_estado(123, db_path) is None
    assert db.eliminar_estado(123, db_path) is False


def test_limpiar_estados_expirados(db_path):
    db.guardar_estado(
        chat_id=1,
        estado_actual="VIEJO",
        timestamp="2026-11-20T10:00:00",
        db_path=db_path,
    )
    db.guardar_estado(
        chat_id=2,
        estado_actual="VIGENTE",
        timestamp="2026-11-20T12:30:00",
        db_path=db_path,
    )

    expirados = db.limpiar_estados_expirados(
        ttl_horas=1, ahora="2026-11-20T13:00:00", db_path=db_path
    )
    assert [fila["chat_id"] for fila in expirados] == [1]
    assert db.obtener_estado(1, db_path) is None
    assert db.obtener_estado(2, db_path) is not None
