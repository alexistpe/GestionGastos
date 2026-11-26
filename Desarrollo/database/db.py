"""Capa de acceso a SQLite.

Todas las funciones abren una conexión corta mediante `conectar`, aplican los
PRAGMA necesarios y confirman o revierten la transacción automáticamente.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Mapping

import config

_DIRECTORIO = Path(__file__).resolve().parent
SCHEMA_PATH = _DIRECTORIO / "schema.sql"
SEED_PATH = _DIRECTORIO / "seed.sql"

BALANCES = ("INGRESO", "EGRESO")
TIPOS_AVISO = ("ETIQUETA", "MONTO_TOTAL")
CAMPOS_COMPROBANTE = {"fecha", "destino", "monto", "balance", "id_etiqueta"}


@contextmanager
def conectar(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Abre una conexión configurada y garantiza commit/rollback y cierre."""
    ruta = Path(db_path) if db_path is not None else Path(config.DB_PATH)
    if str(ruta) != ":memory:":
        ruta.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(ruta), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    if str(ruta) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | Path | None = None) -> None:
    """Aplica schema y seed de forma idempotente."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    seed = SEED_PATH.read_text(encoding="utf-8")
    with conectar(db_path) as conn:
        conn.executescript(schema)
        conn.executescript(seed)


def _fila(fila: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(fila) if fila is not None else None


def _a_fecha(valor: date | datetime | str | None) -> date:
    if valor is None:
        return date.today()
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(valor)


def _timestamp(valor: datetime | str | None = None) -> str:
    if valor is None:
        return datetime.now().isoformat(timespec="seconds")
    if isinstance(valor, datetime):
        return valor.isoformat(timespec="seconds")
    return valor


def _limpiar_texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


# --------------------------------------------------------------------------- #
# Etiquetas
# --------------------------------------------------------------------------- #

def crear_etiqueta(
    nombre: str, es_rutina: bool = False, db_path: str | Path | None = None
) -> int:
    with conectar(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO etiquetas (nombre, es_rutina) VALUES (?, ?)",
            (nombre, int(bool(es_rutina))),
        )
        return int(cur.lastrowid)


def obtener_etiqueta(
    id_etiqueta: int, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with conectar(db_path) as conn:
        fila = conn.execute(
            "SELECT * FROM etiquetas WHERE id = ?", (id_etiqueta,)
        ).fetchone()
        return _fila(fila)


def obtener_etiqueta_por_nombre(
    nombre: str, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with conectar(db_path) as conn:
        fila = conn.execute(
            "SELECT * FROM etiquetas WHERE nombre = ?", (nombre,)
        ).fetchone()
        return _fila(fila)


def listar_etiquetas(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with conectar(db_path) as conn:
        filas = conn.execute(
            "SELECT * FROM etiquetas ORDER BY es_rutina DESC, nombre ASC"
        ).fetchall()
        return [dict(fila) for fila in filas]


def etiqueta_en_uso(
    id_etiqueta: int, db_path: str | Path | None = None
) -> bool:
    with conectar(db_path) as conn:
        fila = conn.execute(
            "SELECT EXISTS(SELECT 1 FROM comprobantes WHERE id_etiqueta = ?) AS usado",
            (id_etiqueta,),
        ).fetchone()
        return bool(fila["usado"])


def eliminar_etiqueta(
    id_etiqueta: int, db_path: str | Path | None = None
) -> bool:
    with conectar(db_path) as conn:
        cur = conn.execute("DELETE FROM etiquetas WHERE id = ?", (id_etiqueta,))
        return cur.rowcount > 0


# --------------------------------------------------------------------------- #
# Comprobantes
# --------------------------------------------------------------------------- #

def crear_comprobante(
    fecha: date | datetime | str,
    monto: float,
    balance: str,
    id_etiqueta: int,
    destino: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    balance_normalizado = str(balance).upper()
    if balance_normalizado not in BALANCES:
        raise ValueError("El balance debe ser INGRESO o EGRESO.")
    with conectar(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO comprobantes (fecha, destino, monto, balance, id_etiqueta)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _a_fecha(fecha).isoformat(),
                _limpiar_texto(destino),
                float(monto),
                balance_normalizado,
                int(id_etiqueta),
            ),
        )
        return int(cur.lastrowid)


def obtener_comprobante(
    id_comprobante: int, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with conectar(db_path) as conn:
        fila = conn.execute(
            """
            SELECT c.id, c.fecha, c.destino, c.monto, c.balance,
                   c.id_etiqueta, e.nombre AS etiqueta
            FROM comprobantes c
            JOIN etiquetas e ON e.id = c.id_etiqueta
            WHERE c.id = ?
            """,
            (id_comprobante,),
        ).fetchone()
        return _fila(fila)


def listar_comprobantes(
    db_path: str | Path | None = None,
    limite: int | None = None,
    offset: int = 0,
    desde: date | datetime | str | None = None,
    hasta: date | datetime | str | None = None,
) -> list[dict[str, Any]]:
    condiciones: list[str] = []
    parametros: list[Any] = []

    if desde is not None:
        condiciones.append("c.fecha >= ?")
        parametros.append(_a_fecha(desde).isoformat())
    if hasta is not None:
        condiciones.append("c.fecha <= ?")
        parametros.append(_a_fecha(hasta).isoformat())
    if desde is not None and hasta is not None and _a_fecha(desde) > _a_fecha(hasta):
        raise ValueError("La fecha inicial no puede ser posterior a la final.")

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    if limite is None:
        limit_sql = "LIMIT -1 OFFSET ?"
        parametros.append(int(offset))
    else:
        limit_sql = "LIMIT ? OFFSET ?"
        parametros.extend([int(limite), int(offset)])

    consulta = f"""
        SELECT c.id, c.fecha, c.destino, c.monto, c.balance,
               c.id_etiqueta, e.nombre AS etiqueta
        FROM comprobantes c
        JOIN etiquetas e ON e.id = c.id_etiqueta
        {where}
        ORDER BY c.fecha DESC, c.id DESC
        {limit_sql}
    """

    with conectar(db_path) as conn:
        filas = conn.execute(consulta, tuple(parametros)).fetchall()
        return [dict(fila) for fila in filas]


def ultimos_comprobantes(
    limite: int = 10, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    return listar_comprobantes(db_path=db_path, limite=limite)


def actualizar_comprobante(
    id_comprobante: int,
    campos: Mapping[str, Any],
    db_path: str | Path | None = None,
) -> bool:
    datos = {clave: valor for clave, valor in campos.items() if clave in CAMPOS_COMPROBANTE}
    if not datos:
        return False

    if "fecha" in datos:
        datos["fecha"] = _a_fecha(datos["fecha"]).isoformat()
    if "monto" in datos:
        datos["monto"] = float(datos["monto"])
    if "balance" in datos:
        datos["balance"] = str(datos["balance"]).upper()
    if "id_etiqueta" in datos:
        datos["id_etiqueta"] = int(datos["id_etiqueta"])
    if "destino" in datos:
        datos["destino"] = _limpiar_texto(datos["destino"])

    asignaciones = ", ".join(f"{clave} = ?" for clave in datos)
    valores = list(datos.values())
    valores.append(id_comprobante)

    with conectar(db_path) as conn:
        cur = conn.execute(
            f"UPDATE comprobantes SET {asignaciones} WHERE id = ?",
            tuple(valores),
        )
        return cur.rowcount > 0


def eliminar_comprobante(
    id_comprobante: int, db_path: str | Path | None = None
) -> bool:
    with conectar(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM comprobantes WHERE id = ?", (id_comprobante,)
        )
        return cur.rowcount > 0


def contar_comprobantes(db_path: str | Path | None = None) -> int:
    with conectar(db_path) as conn:
        fila = conn.execute("SELECT COUNT(*) AS total FROM comprobantes").fetchone()
        return int(fila["total"])


# --------------------------------------------------------------------------- #
# Avisos
# --------------------------------------------------------------------------- #

def crear_o_actualizar_aviso(
    tipo: str,
    monto_limite: float,
    id_etiqueta: int | None = None,
    activo: bool = True,
    db_path: str | Path | None = None,
) -> int:
    tipo_normalizado = str(tipo).upper()
    if tipo_normalizado not in TIPOS_AVISO:
        raise ValueError("El tipo de aviso debe ser ETIQUETA o MONTO_TOTAL.")
    if tipo_normalizado == "ETIQUETA" and id_etiqueta is None:
        raise ValueError("Un aviso por etiqueta necesita id_etiqueta.")
    if tipo_normalizado == "MONTO_TOTAL" and id_etiqueta is not None:
        raise ValueError("Un aviso de monto total no lleva id_etiqueta.")

    with conectar(db_path) as conn:
        if tipo_normalizado == "ETIQUETA":
            fila = conn.execute(
                "SELECT id FROM avisos WHERE tipo = 'ETIQUETA' AND id_etiqueta = ?",
                (int(id_etiqueta),),
            ).fetchone()
        else:
            fila = conn.execute(
                "SELECT id FROM avisos WHERE tipo = 'MONTO_TOTAL'"
            ).fetchone()

        if fila is not None:
            conn.execute(
                "UPDATE avisos SET monto_limite = ?, activo = ? WHERE id = ?",
                (float(monto_limite), int(bool(activo)), int(fila["id"])),
            )
            return int(fila["id"])

        cur = conn.execute(
            """
            INSERT INTO avisos (tipo, id_etiqueta, monto_limite, activo)
            VALUES (?, ?, ?, ?)
            """,
            (
                tipo_normalizado,
                int(id_etiqueta) if id_etiqueta is not None else None,
                float(monto_limite),
                int(bool(activo)),
            ),
        )
        return int(cur.lastrowid)


def obtener_aviso(
    id_aviso: int, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with conectar(db_path) as conn:
        fila = conn.execute(
            """
            SELECT a.id, a.tipo, a.id_etiqueta, e.nombre AS etiqueta,
                   a.monto_limite, a.activo
            FROM avisos a
            LEFT JOIN etiquetas e ON e.id = a.id_etiqueta
            WHERE a.id = ?
            """,
            (id_aviso,),
        ).fetchone()
        return _fila(fila)


def listar_avisos(
    solo_activos: bool = True, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    where = "WHERE a.activo = 1" if solo_activos else ""
    with conectar(db_path) as conn:
        filas = conn.execute(
            f"""
            SELECT a.id, a.tipo, a.id_etiqueta, e.nombre AS etiqueta,
                   a.monto_limite, a.activo
            FROM avisos a
            LEFT JOIN etiquetas e ON e.id = a.id_etiqueta
            {where}
            ORDER BY a.tipo ASC, e.nombre ASC
            """
        ).fetchall()
        return [dict(fila) for fila in filas]


def desactivar_aviso(id_aviso: int, db_path: str | Path | None = None) -> bool:
    with conectar(db_path) as conn:
        cur = conn.execute(
            "UPDATE avisos SET activo = 0 WHERE id = ?", (id_aviso,)
        )
        return cur.rowcount > 0


def eliminar_aviso(id_aviso: int, db_path: str | Path | None = None) -> bool:
    with conectar(db_path) as conn:
        cur = conn.execute("DELETE FROM avisos WHERE id = ?", (id_aviso,))
        return cur.rowcount > 0


# --------------------------------------------------------------------------- #
# Configuración y saldo de ahorro
# --------------------------------------------------------------------------- #

CLAVE_SALDO_INICIAL_AHORRO = "saldo_inicial_ahorro"


def obtener_configuracion(
    clave: str, db_path: str | Path | None = None
) -> str | None:
    with conectar(db_path) as conn:
        fila = conn.execute(
            "SELECT valor FROM configuracion WHERE clave = ?", (clave,)
        ).fetchone()
        return str(fila["valor"]) if fila is not None else None


def guardar_configuracion(
    clave: str, valor: str, db_path: str | Path | None = None
) -> None:
    with conectar(db_path) as conn:
        conn.execute(
            """
            INSERT INTO configuracion (clave, valor) VALUES (?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
            """,
            (clave, str(valor)),
        )


def obtener_saldo_inicial_ahorro(
    db_path: str | Path | None = None,
) -> float:
    valor = obtener_configuracion(CLAVE_SALDO_INICIAL_AHORRO, db_path)
    try:
        return float(valor) if valor is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def guardar_saldo_inicial_ahorro(
    monto: float, db_path: str | Path | None = None
) -> None:
    guardar_configuracion(
        CLAVE_SALDO_INICIAL_AHORRO, str(float(monto)), db_path
    )


def _saldo_ahorro(inclusive: bool, fecha, db_path=None) -> float:
    fecha_iso = _a_fecha(fecha).isoformat()
    operador = "<=" if inclusive else "<"
    with conectar(db_path) as conn:
        fila_config = conn.execute(
            "SELECT valor FROM configuracion WHERE clave = ?",
            (CLAVE_SALDO_INICIAL_AHORRO,),
        ).fetchone()
        try:
            inicial = (
                float(fila_config["valor"]) if fila_config is not None else 0.0
            )
        except (TypeError, ValueError):
            inicial = 0.0

        fila = conn.execute(
            f"""
            SELECT COALESCE(SUM(
                CASE WHEN c.balance = 'EGRESO' THEN c.monto ELSE -c.monto END
            ), 0) AS saldo
            FROM comprobantes c
            JOIN etiquetas e ON e.id = c.id_etiqueta
            WHERE e.nombre = 'ahorro' AND c.fecha {operador} ?
            """,
            (fecha_iso,),
        ).fetchone()
        return inicial + float(fila["saldo"])


def saldo_ahorro_antes(
    fecha, db_path: str | Path | None = None
) -> float:
    """Saldo de ahorro al inicio de una fecha (sin incluir ese día)."""
    return _saldo_ahorro(False, fecha, db_path)


def saldo_ahorro_hasta(
    fecha, db_path: str | Path | None = None
) -> float:
    """Saldo de ahorro al cierre de una fecha (incluyéndola)."""
    return _saldo_ahorro(True, fecha, db_path)


# --------------------------------------------------------------------------- #
# Período actual
# --------------------------------------------------------------------------- #

def inicio_periodo_actual(
    hoy: date | datetime | str | None = None,
    db_path: str | Path | None = None,
) -> str:
    fecha_hoy = _a_fecha(hoy)
    with conectar(db_path) as conn:
        fila = conn.execute(
            """
            SELECT MAX(c.fecha) AS fecha
            FROM comprobantes c
            JOIN etiquetas e ON e.id = c.id_etiqueta
            WHERE e.nombre = 'cuota'
              AND c.balance = 'INGRESO'
              AND c.fecha <= ?
            """,
            (fecha_hoy.isoformat(),),
        ).fetchone()

        if fila is not None and fila["fecha"]:
            return str(fila["fecha"])
        return fecha_hoy.replace(day=1).isoformat()


def listar_comprobantes_periodo(
    inicio: date | datetime | str | None = None,
    fin: date | datetime | str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    fecha_fin = _a_fecha(fin)
    fecha_inicio = (
        _a_fecha(inicio)
        if inicio is not None
        else date.fromisoformat(inicio_periodo_actual(fecha_fin, db_path))
    )
    if fecha_inicio > fecha_fin:
        raise ValueError("La fecha inicial no puede ser posterior a la final.")
    return listar_comprobantes(
        db_path=db_path, desde=fecha_inicio, hasta=fecha_fin
    )


# --------------------------------------------------------------------------- #
# Estado conversacional
# --------------------------------------------------------------------------- #

def guardar_estado(
    chat_id: int,
    estado_actual: str,
    contexto: Mapping[str, Any] | None = None,
    id_comprobante: int | None = None,
    nombre_conversacion: str = "comprobante",
    timestamp: datetime | str | None = None,
    db_path: str | Path | None = None,
) -> None:
    contexto_json = (
        json.dumps(contexto, ensure_ascii=False) if contexto is not None else None
    )
    with conectar(db_path) as conn:
        conn.execute(
            """
            INSERT INTO sesion_estado (
                chat_id, nombre_conversacion, estado_actual,
                contexto_json, id_comprobante, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                nombre_conversacion = excluded.nombre_conversacion,
                estado_actual = excluded.estado_actual,
                contexto_json = excluded.contexto_json,
                id_comprobante = excluded.id_comprobante,
                timestamp = excluded.timestamp
            """,
            (
                int(chat_id),
                nombre_conversacion,
                estado_actual,
                contexto_json,
                int(id_comprobante) if id_comprobante is not None else None,
                _timestamp(timestamp),
            ),
        )


def obtener_estado(
    chat_id: int, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    with conectar(db_path) as conn:
        fila = conn.execute(
            "SELECT * FROM sesion_estado WHERE chat_id = ?", (int(chat_id),)
        ).fetchone()
        if fila is None:
            return None
        datos = dict(fila)
        datos["contexto"] = (
            json.loads(datos["contexto_json"]) if datos["contexto_json"] else None
        )
        return datos


def listar_estados(
    nombre_conversacion: str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    if nombre_conversacion is None:
        consulta = "SELECT * FROM sesion_estado ORDER BY timestamp ASC"
        parametros: tuple[Any, ...] = ()
    else:
        consulta = (
            "SELECT * FROM sesion_estado "
            "WHERE nombre_conversacion = ? ORDER BY timestamp ASC"
        )
        parametros = (nombre_conversacion,)

    with conectar(db_path) as conn:
        filas = conn.execute(consulta, parametros).fetchall()
        resultado: list[dict[str, Any]] = []
        for fila in filas:
            datos = dict(fila)
            datos["contexto"] = (
                json.loads(datos["contexto_json"])
                if datos["contexto_json"]
                else None
            )
            resultado.append(datos)
        return resultado


def eliminar_estado(
    chat_id: int, db_path: str | Path | None = None
) -> bool:
    with conectar(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM sesion_estado WHERE chat_id = ?", (int(chat_id),)
        )
        return cur.rowcount > 0


def limpiar_estados_expirados(
    ttl_horas: int = 1,
    ahora: datetime | str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    if ahora is None:
        momento = datetime.now()
    elif isinstance(ahora, datetime):
        momento = ahora
    else:
        momento = datetime.fromisoformat(ahora)

    limite = (momento - timedelta(hours=ttl_horas)).isoformat(timespec="seconds")
    with conectar(db_path) as conn:
        filas = conn.execute(
            """
            SELECT chat_id, nombre_conversacion, estado_actual, timestamp
            FROM sesion_estado
            WHERE timestamp < ?
            """,
            (limite,),
        ).fetchall()
        expirados = [dict(fila) for fila in filas]
        if expirados:
            conn.executemany(
                "DELETE FROM sesion_estado WHERE chat_id = ?",
                [(fila["chat_id"],) for fila in expirados],
            )
        return expirados


# --------------------------------------------------------------------------- #
# Alertas disparadas
# --------------------------------------------------------------------------- #

def registrar_aviso_disparado(
    clave: str, periodo: str, db_path: str | Path | None = None
) -> bool:
    """Registra la clave/periodo. Devuelve True si es la primera vez."""
    with conectar(db_path) as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO avisos_disparados (clave, periodo, disparado_en)
            VALUES (?, ?, ?)
            """,
            (clave, periodo, _timestamp()),
        )
        return cur.rowcount > 0


def ya_disparado(
    clave: str, periodo: str, db_path: str | Path | None = None
) -> bool:
    with conectar(db_path) as conn:
        fila = conn.execute(
            """
            SELECT EXISTS(
                SELECT 1 FROM avisos_disparados
                WHERE clave = ? AND periodo = ?
            ) AS disparado
            """,
            (clave, periodo),
        ).fetchone()
        return bool(fila["disparado"])


def limpiar_avisos_disparados(
    periodo: str, db_path: str | Path | None = None
) -> int:
    with conectar(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM avisos_disparados WHERE periodo = ?", (periodo,)
        )
        return cur.rowcount
