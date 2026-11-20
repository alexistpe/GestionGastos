"""Clase orquestadora de la lógica de negocio.

``Gestion`` coordina la base de datos, los cálculos de ``Resumen`` y la
evaluación de ``Aviso``. No depende de Telegram ni de Gemini.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from database import db
from modules import aviso as modulo_aviso
from modules.resumen import Resumen, TipoResumen
from utils import parsers
from utils.parsers import ErrorParseo


class ErrorGestion(Exception):
    """Error de negocio con un mensaje apto para el usuario."""


class Gestion:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = db_path

    # ------------------------------------------------------------------ #
    # Normalización
    # ------------------------------------------------------------------ #

    def _normalizar_fecha(self, fecha: Any) -> str:
        if fecha is None:
            return date.today().isoformat()
        if isinstance(fecha, datetime):
            return fecha.date().isoformat()
        if isinstance(fecha, date):
            return fecha.isoformat()
        try:
            return parsers.parsear_fecha(str(fecha))
        except ErrorParseo as exc:
            raise ErrorGestion(str(exc)) from exc

    def _a_fecha(self, valor: Any) -> date:
        if valor is None:
            return date.today()
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        return date.fromisoformat(self._normalizar_fecha(valor))

    def _normalizar_monto(self, monto: Any) -> float:
        if isinstance(monto, (int, float)) and not isinstance(monto, bool):
            if float(monto) <= 0:
                raise ErrorGestion("El monto debe ser mayor que cero.")
            return float(monto)
        try:
            return parsers.parsear_monto(str(monto))
        except ErrorParseo as exc:
            raise ErrorGestion(str(exc)) from exc

    def _normalizar_balance(self, balance: Any) -> str:
        valor = str(balance).upper()
        if valor not in ("INGRESO", "EGRESO"):
            raise ErrorGestion("El balance debe ser INGRESO o EGRESO.")
        return valor

    def _resolver_etiqueta(
        self, nombre: str | None = None, id_etiqueta: int | None = None
    ) -> int:
        if nombre is not None and id_etiqueta is not None:
            raise ErrorGestion(
                "Indicá la etiqueta por nombre o por id, no ambas."
            )

        if id_etiqueta is not None:
            etiqueta = db.obtener_etiqueta(int(id_etiqueta), self.db_path)
            if etiqueta is None:
                raise ErrorGestion(
                    f"No existe la etiqueta con id {id_etiqueta}."
                )
            return int(etiqueta["id"])

        if not nombre:
            raise ErrorGestion("Falta la etiqueta.")

        try:
            nombre_normalizado = parsers.normalizar_nombre_etiqueta(nombre)
        except ErrorParseo as exc:
            raise ErrorGestion(str(exc)) from exc

        etiqueta = db.obtener_etiqueta_por_nombre(
            nombre_normalizado, self.db_path
        )
        if etiqueta is None:
            raise ErrorGestion(
                f"La etiqueta '{nombre_normalizado}' no existe. "
                f"Creala con: etiqueta {nombre_normalizado}"
            )
        return int(etiqueta["id"])

    # ------------------------------------------------------------------ #
    # Comprobantes
    # ------------------------------------------------------------------ #

    def registrar_comprobante(
        self,
        monto: Any,
        balance: Any,
        etiqueta: str | None = None,
        id_etiqueta: int | None = None,
        fecha: Any = None,
        destino: str | None = None,
    ) -> dict[str, Any]:
        id_resuelto = self._resolver_etiqueta(etiqueta, id_etiqueta)
        fecha_normalizada = self._normalizar_fecha(fecha)
        monto_normalizado = self._normalizar_monto(monto)
        balance_normalizado = self._normalizar_balance(balance)

        try:
            id_comprobante = db.crear_comprobante(
                fecha=fecha_normalizada,
                monto=monto_normalizado,
                balance=balance_normalizado,
                id_etiqueta=id_resuelto,
                destino=destino,
                db_path=self.db_path,
            )
        except sqlite3.IntegrityError as exc:
            raise ErrorGestion(
                "No se pudo guardar el comprobante: verificá los datos."
            ) from exc

        comprobante = db.obtener_comprobante(id_comprobante, self.db_path)
        return {
            "comprobante": comprobante,
            "avisos": self.evaluar_avisos(),
        }

    def actualizar_comprobante(
        self, id_comprobante: int, cambios: Mapping[str, Any]
    ) -> dict[str, Any]:
        existente = db.obtener_comprobante(id_comprobante, self.db_path)
        if existente is None:
            raise ErrorGestion(f"No existe el comprobante #{id_comprobante}.")

        datos: dict[str, Any] = {}

        if cambios.get("etiqueta") is not None:
            datos["id_etiqueta"] = self._resolver_etiqueta(
                nombre=cambios["etiqueta"]
            )
        if cambios.get("id_etiqueta") is not None:
            if "id_etiqueta" in datos:
                raise ErrorGestion(
                    "Indicá la etiqueta por nombre o por id, no ambas."
                )
            datos["id_etiqueta"] = self._resolver_etiqueta(
                id_etiqueta=cambios["id_etiqueta"]
            )
        if "fecha" in cambios:
            datos["fecha"] = self._normalizar_fecha(cambios["fecha"])
        if "monto" in cambios:
            datos["monto"] = self._normalizar_monto(cambios["monto"])
        if "balance" in cambios:
            datos["balance"] = self._normalizar_balance(cambios["balance"])
        if "destino" in cambios:
            destino = cambios["destino"]
            datos["destino"] = (
                str(destino).strip() if destino is not None else None
            )

        if not datos:
            raise ErrorGestion("No indicaste ningún campo para actualizar.")

        try:
            actualizado = db.actualizar_comprobante(
                id_comprobante, datos, self.db_path
            )
        except sqlite3.IntegrityError as exc:
            raise ErrorGestion(
                "No se pudo actualizar el comprobante: verificá los datos."
            ) from exc

        if not actualizado:
            raise ErrorGestion(f"No existe el comprobante #{id_comprobante}.")

        comprobante = db.obtener_comprobante(id_comprobante, self.db_path)
        return {
            "comprobante": comprobante,
            "avisos": self.evaluar_avisos(),
        }

    def corregir_comprobante(
        self, id_comprobante: int, cambios: Mapping[str, Any]
    ) -> dict[str, Any]:
        return self.actualizar_comprobante(id_comprobante, cambios)

    def eliminar_comprobante(self, id_comprobante: int) -> bool:
        if db.obtener_comprobante(id_comprobante, self.db_path) is None:
            raise ErrorGestion(f"No existe el comprobante #{id_comprobante}.")
        return db.eliminar_comprobante(id_comprobante, self.db_path)

    def obtener_comprobante(
        self, id_comprobante: int
    ) -> dict[str, Any] | None:
        return db.obtener_comprobante(id_comprobante, self.db_path)

    def listar_comprobantes_recientes(
        self, limite: int = 10
    ) -> list[dict[str, Any]]:
        return db.ultimos_comprobantes(limite, self.db_path)

    # ------------------------------------------------------------------ #
    # Análisis
    # ------------------------------------------------------------------ #

    def periodo_actual(self, hoy: Any = None) -> tuple[date, date]:
        fin = self._a_fecha(hoy)
        inicio = date.fromisoformat(
            db.inicio_periodo_actual(fin, self.db_path)
        )
        return inicio, fin

    def generar_resumen(
        self,
        tipo: str | TipoResumen = TipoResumen.MENSUAL,
        desde: Any = None,
        hasta: Any = None,
        hoy: Any = None,
    ) -> Resumen:
        try:
            tipo_enum = (
                tipo
                if isinstance(tipo, TipoResumen)
                else TipoResumen(str(tipo).upper())
            )
        except ValueError as exc:
            raise ErrorGestion(
                "Tipo de resumen inválido. Usá MENSUAL o RANGO."
            ) from exc

        if tipo_enum is TipoResumen.MENSUAL:
            fin = self._a_fecha(hoy)
            inicio = date.fromisoformat(
                db.inicio_periodo_actual(fin, self.db_path)
            )
        else:
            if desde is None or hasta is None:
                raise ErrorGestion(
                    "Para un análisis por rango indicá fecha desde y hasta."
                )
            inicio = self._a_fecha(desde)
            fin = self._a_fecha(hasta)
            if inicio > fin:
                raise ErrorGestion(
                    "La fecha inicial no puede ser posterior a la final."
                )

        comprobantes = db.listar_comprobantes(
            db_path=self.db_path, desde=inicio, hasta=fin
        )
        etiquetas = db.listar_etiquetas(self.db_path)
        avisos = db.listar_avisos(solo_activos=True, db_path=self.db_path)
        return Resumen(
            comprobantes=comprobantes,
            etiquetas=etiquetas,
            avisos=avisos,
            tipo=tipo_enum,
            desde=inicio,
            hasta=fin,
        )

    def conocer_resumen(
        self,
        tipo: str | TipoResumen = TipoResumen.MENSUAL,
        desde: Any = None,
        hasta: Any = None,
        hoy: Any = None,
    ) -> Resumen:
        return self.generar_resumen(tipo, desde, hasta, hoy)

    # ------------------------------------------------------------------ #
    # Alertas
    # ------------------------------------------------------------------ #

    def evaluar_avisos(self, hoy: Any = None) -> list[dict[str, Any]]:
        resumen = self.generar_resumen("MENSUAL", hoy=hoy)
        return modulo_aviso.evaluar_avisos(resumen, self.db_path)

    def generar_aviso(self, hoy: Any = None) -> list[dict[str, Any]]:
        return self.evaluar_avisos(hoy)

    def configurar_alerta_etiqueta(
        self, nombre: str, monto_limite: Any
    ) -> dict[str, Any]:
        id_etiqueta = self._resolver_etiqueta(nombre=nombre)
        monto = self._normalizar_monto(monto_limite)
        id_aviso = db.crear_o_actualizar_aviso(
            "ETIQUETA",
            monto,
            id_etiqueta=id_etiqueta,
            db_path=self.db_path,
        )
        return db.obtener_aviso(id_aviso, self.db_path)

    def configurar_alerta_total(self, monto_limite: Any) -> dict[str, Any]:
        monto = self._normalizar_monto(monto_limite)
        id_aviso = db.crear_o_actualizar_aviso(
            "MONTO_TOTAL", monto, db_path=self.db_path
        )
        return db.obtener_aviso(id_aviso, self.db_path)

    def listar_alertas(
        self, solo_activos: bool = True
    ) -> list[dict[str, Any]]:
        return db.listar_avisos(solo_activos, self.db_path)

    def conocer_aviso(self, id_aviso: int) -> dict[str, Any] | None:
        return db.obtener_aviso(id_aviso, self.db_path)

    # ------------------------------------------------------------------ #
    # Etiquetas
    # ------------------------------------------------------------------ #

    def crear_etiqueta(
        self, nombre: str, es_rutina: bool = False
    ) -> dict[str, Any]:
        try:
            nombre_normalizado = parsers.normalizar_nombre_etiqueta(nombre)
        except ErrorParseo as exc:
            raise ErrorGestion(str(exc)) from exc

        try:
            id_etiqueta = db.crear_etiqueta(
                nombre_normalizado,
                es_rutina=es_rutina,
                db_path=self.db_path,
            )
        except sqlite3.IntegrityError as exc:
            raise ErrorGestion(
                f"La etiqueta '{nombre_normalizado}' ya existe."
            ) from exc

        return db.obtener_etiqueta(id_etiqueta, self.db_path)

    def eliminar_etiqueta(self, nombre: str) -> str:
        try:
            nombre_normalizado = parsers.normalizar_nombre_etiqueta(nombre)
        except ErrorParseo as exc:
            raise ErrorGestion(str(exc)) from exc

        etiqueta = db.obtener_etiqueta_por_nombre(
            nombre_normalizado, self.db_path
        )
        if etiqueta is None:
            raise ErrorGestion(f"La etiqueta '{nombre_normalizado}' no existe.")
        if db.etiqueta_en_uso(etiqueta["id"], self.db_path):
            raise ErrorGestion(
                f"La etiqueta '{nombre_normalizado}' tiene comprobantes "
                "asociados y no se puede eliminar."
            )
        db.eliminar_etiqueta(etiqueta["id"], self.db_path)
        return nombre_normalizado

    def listar_etiquetas(self) -> list[dict[str, Any]]:
        return db.listar_etiquetas(self.db_path)

    def conocer_etiqueta(self, nombre: str) -> dict[str, Any] | None:
        try:
            nombre_normalizado = parsers.normalizar_nombre_etiqueta(nombre)
        except ErrorParseo as exc:
            raise ErrorGestion(str(exc)) from exc
        return db.obtener_etiqueta_por_nombre(
            nombre_normalizado, self.db_path
        )
