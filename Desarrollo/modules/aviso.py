"""Evaluación y disparo de alertas.

Las alertas configuradas por el usuario viven en la tabla ``avisos``. Las
alertas internas (balance negativo, rutina completa, extracciones de ahorro) se
calculan a partir del ``Resumen``. Todas usan ``avisos_disparados`` para emitirse
una sola vez por período.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from database import db
from modules.resumen import Resumen, TipoResumen
from utils.formato import formatear_monto


@dataclass
class Aviso:
    id: int | None
    tipo: str
    monto_limite: float
    id_etiqueta: int | None = None
    etiqueta: str | None = None
    activo: bool = True

    @classmethod
    def desde_fila(cls, fila: dict[str, Any]) -> "Aviso":
        return cls(
            id=fila.get("id"),
            tipo=fila["tipo"],
            monto_limite=float(fila["monto_limite"]),
            id_etiqueta=fila.get("id_etiqueta"),
            etiqueta=fila.get("etiqueta"),
            activo=bool(fila.get("activo", 1)),
        )

    def clave(self) -> str:
        if self.tipo == "ETIQUETA":
            if self.etiqueta == "ahorro":
                return f"ETIQUETA_AHORRO:{self.id}"
            return f"ETIQUETA:{self.id}"
        return "MONTO_TOTAL"

    def evaluar(self, resumen: Resumen) -> str | None:
        if self.tipo == "ETIQUETA":
            if self.etiqueta == "ahorro":
                extraido = resumen.ahorro_extraido
                if extraido > self.monto_limite:
                    return (
                        "⚠️ Extracciones de ahorro superaron el límite: "
                        f"{formatear_monto(extraido)} de "
                        f"{formatear_monto(self.monto_limite)}."
                    )
                return None

            gasto = next(
                (
                    item["monto"]
                    for item in resumen.gastos_por_etiqueta
                    if item["etiqueta"] == self.etiqueta
                ),
                0.0,
            )
            if gasto > self.monto_limite:
                return (
                    f"⚠️ La etiqueta {self.etiqueta} superó su límite: "
                    f"{formatear_monto(gasto)} de "
                    f"{formatear_monto(self.monto_limite)}."
                )
            return None

        if self.tipo == "MONTO_TOTAL":
            if resumen.monto_saliente > self.monto_limite:
                return (
                    "⚠️ El gasto total del período superó el límite: "
                    f"{formatear_monto(resumen.monto_saliente)} de "
                    f"{formatear_monto(self.monto_limite)}."
                )
            return None

        return None


def _registrar(
    clave: str,
    tipo: str,
    mensaje: str,
    periodo: str | None,
    db_path: str | Path | None,
) -> dict[str, Any] | None:
    if db.registrar_aviso_disparado(clave, periodo or "", db_path):
        return {
            "clave": clave,
            "tipo": tipo,
            "mensaje": mensaje,
            "periodo": periodo,
        }
    return None


def evaluar_avisos(
    resumen: Resumen, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Devuelve las alertas que corresponden emitir para el resumen dado."""
    periodo = resumen.desde.isoformat() if resumen.desde else None
    disparados: list[dict[str, Any]] = []

    if resumen.monto_neto < 0:
        alerta = _registrar(
            "BALANCE_NEGATIVO",
            "balance",
            (
                "⚠️ Balance negativo del período: "
                f"ingresos {formatear_monto(resumen.monto_ingresado)}, "
                f"gastos {formatear_monto(resumen.monto_saliente)}, "
                f"neto {formatear_monto(resumen.monto_neto)}."
            ),
            periodo,
            db_path,
        )
        if alerta:
            disparados.append(alerta)

    if resumen.tipo is TipoResumen.MENSUAL and resumen.rutina_completa:
        etiquetas = ", ".join(
            item["etiqueta"] for item in resumen.rutina if item["completado"]
        )
        alerta = _registrar(
            "RUTINA",
            "rutina",
            f"✅ Rutina completa: ya registraste todos los gastos fijos ({etiquetas}).",
            periodo,
            db_path,
        )
        if alerta:
            disparados.append(alerta)

    for fila in resumen.avisos:
        aviso = Aviso.desde_fila(fila)
        if not aviso.activo:
            continue
        mensaje = aviso.evaluar(resumen)
        if mensaje is None:
            continue
        alerta = _registrar(
            aviso.clave(), "aviso", mensaje, periodo, db_path
        )
        if alerta:
            disparados.append(alerta)

    if resumen.monto_ahorro < 0:
        alerta = _registrar(
            "AHORRO_NEGATIVO",
            "ahorro",
            (
                "⚠️ Balance de ahorro negativo en el período: "
                f"depositado {formatear_monto(resumen.ahorro_depositado)}, "
                f"extraído {formatear_monto(resumen.ahorro_extraido)}, "
                f"neto {formatear_monto(resumen.monto_ahorro)}."
            ),
            periodo,
            db_path,
        )
        if alerta:
            disparados.append(alerta)
    elif (
        resumen.ahorro_extraido > 0
        and resumen.ahorro_extraido > resumen.monto_neto
    ):
        alerta = _registrar(
            "AHORRO",
            "ahorro",
            (
                "⚠️ Extracciones de ahorro "
                f"({formatear_monto(resumen.ahorro_extraido)}) "
                "superan el ingreso neto del período "
                f"({formatear_monto(resumen.monto_neto)})."
            ),
            periodo,
            db_path,
        )
        if alerta:
            disparados.append(alerta)

    return disparados
