"""Cálculos de análisis financiero.

La clase ``Resumen`` recibe los comprobantes, etiquetas y avisos de un período y
expone los totales, agrupaciones y la comparación con la rutina. No conoce
Telegram ni Gemini: solo trabaja con datos.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from utils.formato import formatear_fecha, formatear_monto


class TipoResumen(str, Enum):
    MENSUAL = "MENSUAL"
    RANGO = "RANGO"


def _a_fecha(valor: date | datetime | str | None) -> date | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(valor)


class Resumen:
    """Resumen financiero de un período."""

    def __init__(
        self,
        comprobantes: list[dict[str, Any]],
        etiquetas: list[dict[str, Any]],
        avisos: list[dict[str, Any]] | None = None,
        tipo: TipoResumen | str = TipoResumen.MENSUAL,
        desde: date | datetime | str | None = None,
        hasta: date | datetime | str | None = None,
    ) -> None:
        self.comprobantes = list(comprobantes)
        self.etiquetas_lista = list(etiquetas)
        self.etiquetas = {etiqueta["nombre"]: etiqueta for etiqueta in etiquetas}
        self.avisos = list(avisos or [])
        self.tipo = (
            tipo
            if isinstance(tipo, TipoResumen)
            else TipoResumen(str(tipo).upper())
        )
        self.desde = _a_fecha(desde)
        self.hasta = _a_fecha(hasta)

        self.monto_ingresado = self.calcular_monto_ingresado()
        self.monto_saliente = self.calcular_monto_saliente()
        self.monto_neto = self.calcular_monto_neto()
        self.monto_ahorro = self.calcular_ahorro()
        self.gastos_por_etiqueta = self.calcular_gastos_por_etiqueta()
        self.ingresos = self.calcular_ingresos()
        self.rutina = self.calcular_rutina()
        self.monto_gastado_rutina = sum(item["gastado"] for item in self.rutina)
        pendientes = [
            item["pendiente"]
            for item in self.rutina
            if item["pendiente"] is not None
        ]
        self.monto_pendiente_rutina = sum(pendientes) if pendientes else None
        self.rutina_completa = bool(self.rutina) and all(
            item["completado"] for item in self.rutina
        )
        self.gastos_no_esenciales = self.calcular_gastos_no_esenciales()
        self.monto_gastos_no_esenciales = sum(
            item["monto"] for item in self.gastos_no_esenciales
        )

    # ------------------------------------------------------------------ #
    # Cálculos
    # ------------------------------------------------------------------ #

    def calcular_monto_ingresado(self) -> float:
        return sum(
            float(comprobante["monto"])
            for comprobante in self.comprobantes
            if comprobante["balance"] == "INGRESO"
        )

    def calcular_monto_saliente(self) -> float:
        return sum(
            float(comprobante["monto"])
            for comprobante in self.comprobantes
            if comprobante["balance"] == "EGRESO"
        )

    def calcular_monto_neto(self) -> float:
        return self.monto_ingresado - self.monto_saliente

    def calcular_ahorro(self) -> float:
        """Ahorro neto: egresos a ahorro menos extracciones desde ahorro."""
        egresos = sum(
            float(comprobante["monto"])
            for comprobante in self.comprobantes
            if comprobante["balance"] == "EGRESO"
            and comprobante["etiqueta"] == "ahorro"
        )
        ingresos = sum(
            float(comprobante["monto"])
            for comprobante in self.comprobantes
            if comprobante["balance"] == "INGRESO"
            and comprobante["etiqueta"] == "ahorro"
        )
        return egresos - ingresos

    def calcular_gastos_por_etiqueta(self) -> list[dict[str, Any]]:
        totales: dict[str, float] = {}
        for comprobante in self.comprobantes:
            if comprobante["balance"] != "EGRESO":
                continue
            etiqueta = comprobante["etiqueta"]
            totales[etiqueta] = totales.get(etiqueta, 0.0) + float(
                comprobante["monto"]
            )
        return [
            {"etiqueta": etiqueta, "monto": monto}
            for etiqueta, monto in sorted(
                totales.items(), key=lambda item: (-item[1], item[0])
            )
        ]

    def calcular_ingresos(self) -> list[dict[str, Any]]:
        ingresos = [
            comprobante
            for comprobante in self.comprobantes
            if comprobante["balance"] == "INGRESO"
        ]
        return sorted(
            ingresos,
            key=lambda comprobante: (
                comprobante.get("fecha", ""),
                comprobante.get("id", 0),
            ),
        )

    def calcular_rutina(self) -> list[dict[str, Any]]:
        etiquetas_rutina = sorted(
            (
                etiqueta
                for etiqueta in self.etiquetas_lista
                if etiqueta["es_rutina"] == 1
            ),
            key=lambda etiqueta: etiqueta["nombre"],
        )

        resultado: list[dict[str, Any]] = []
        for etiqueta in etiquetas_rutina:
            nombre = etiqueta["nombre"]
            gastos = [
                comprobante
                for comprobante in self.comprobantes
                if comprobante["balance"] == "EGRESO"
                and comprobante["etiqueta"] == nombre
            ]
            gastado = sum(float(comprobante["monto"]) for comprobante in gastos)
            aviso = next(
                (
                    aviso
                    for aviso in self.avisos
                    if aviso["tipo"] == "ETIQUETA"
                    and aviso.get("etiqueta") == nombre
                    and aviso.get("activo", 1)
                ),
                None,
            )
            presupuesto = (
                float(aviso["monto_limite"]) if aviso is not None else None
            )
            pendiente = (
                max(presupuesto - gastado, 0.0)
                if presupuesto is not None
                else None
            )
            resultado.append(
                {
                    "etiqueta": nombre,
                    "gastado": gastado,
                    "registros": len(gastos),
                    "presupuesto": presupuesto,
                    "pendiente": pendiente,
                    "completado": len(gastos) > 0,
                }
            )
        return resultado

    def calcular_gastos_no_esenciales(self) -> list[dict[str, Any]]:
        """Gastos fuera de la rutina y fuera de la etiqueta ``ahorro``.

        ``ahorro`` no se considera gasto no esencial porque es una transferencia
        entre cuentas, no una pérdida de dinero. Su análisis es independiente.
        """
        etiquetas_rutina = {
            etiqueta["nombre"]
            for etiqueta in self.etiquetas_lista
            if etiqueta["es_rutina"] == 1
        }
        totales: dict[str, float] = {}
        for comprobante in self.comprobantes:
            if comprobante["balance"] != "EGRESO":
                continue
            etiqueta = comprobante["etiqueta"]
            if etiqueta in etiquetas_rutina or etiqueta == "ahorro":
                continue
            totales[etiqueta] = totales.get(etiqueta, 0.0) + float(
                comprobante["monto"]
            )
        return [
            {"etiqueta": etiqueta, "monto": monto}
            for etiqueta, monto in sorted(
                totales.items(), key=lambda item: (-item[1], item[0])
            )
        ]

    # ------------------------------------------------------------------ #
    # Salidas
    # ------------------------------------------------------------------ #

    def a_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo.value,
            "desde": self.desde.isoformat() if self.desde else None,
            "hasta": self.hasta.isoformat() if self.hasta else None,
            "monto_ingresado": self.monto_ingresado,
            "monto_saliente": self.monto_saliente,
            "monto_neto": self.monto_neto,
            "monto_ahorro": self.monto_ahorro,
            "gastos_por_etiqueta": self.gastos_por_etiqueta,
            "ingresos": self.ingresos,
            "comprobantes": self.comprobantes,
            "rutina": self.rutina,
            "monto_gastado_rutina": self.monto_gastado_rutina,
            "monto_pendiente_rutina": self.monto_pendiente_rutina,
            "rutina_completa": self.rutina_completa,
            "gastos_no_esenciales": self.gastos_no_esenciales,
            "monto_gastos_no_esenciales": self.monto_gastos_no_esenciales,
        }

    def a_texto(self) -> str:
        titulo = (
            "📊 Análisis del mes"
            if self.tipo is TipoResumen.MENSUAL
            else "📊 Análisis por rango"
        )
        lineas: list[str] = [titulo]
        if self.desde and self.hasta:
            lineas.append(
                f"Período: {formatear_fecha(self.desde)} → {formatear_fecha(self.hasta)}"
            )

        lineas.extend(
            [
                "",
                f"💵 Ingresos: {formatear_monto(self.monto_ingresado)}",
                f"💸 Gastos: {formatear_monto(self.monto_saliente)}",
                f"⚖️ Neto: {formatear_monto(self.monto_neto)}",
                "",
                "🏷️ Gastos por etiqueta",
            ]
        )
        if self.gastos_por_etiqueta:
            for item in self.gastos_por_etiqueta:
                lineas.append(
                    f"  • {item['etiqueta']}: {formatear_monto(item['monto'])}"
                )
        else:
            lineas.append("  • Sin gastos registrados.")

        lineas.append("")
        lineas.append("🧾 Ingresos detallados")
        if self.ingresos:
            for item in self.ingresos:
                destino = f" · {item['destino']}" if item.get("destino") else ""
                lineas.append(
                    "  • "
                    f"{formatear_fecha(item['fecha'])} · {item['etiqueta']} · "
                    f"{formatear_monto(item['monto'])}{destino}"
                )
        else:
            lineas.append("  • Sin ingresos registrados.")

        lineas.extend(
            ["", f"🐷 Ahorro neto: {formatear_monto(self.monto_ahorro)}"]
        )

        if self.tipo is TipoResumen.MENSUAL:
            lineas.extend(["", "🏠 Rutina"])
            for item in self.rutina:
                if item["presupuesto"] is None:
                    detalle = "sin presupuesto definido"
                else:
                    detalle = f"pendiente: {formatear_monto(item['pendiente'])}"
                estado = "✅" if item["completado"] else "⏳"
                lineas.append(
                    f"  {estado} {item['etiqueta']}: "
                    f"{formatear_monto(item['gastado'])} · {detalle}"
                )
            lineas.append(
                f"  Total rutina: {formatear_monto(self.monto_gastado_rutina)}"
            )
            if self.monto_pendiente_rutina is None:
                lineas.append("  Pendiente rutina: sin presupuesto definido")
            else:
                lineas.append(
                    "  Pendiente rutina: "
                    f"{formatear_monto(self.monto_pendiente_rutina)}"
                )

            lineas.extend(["", "🛍️ Gastos no esenciales"])
            if self.gastos_no_esenciales:
                for item in self.gastos_no_esenciales:
                    lineas.append(
                        f"  • {item['etiqueta']}: {formatear_monto(item['monto'])}"
                    )
            else:
                lineas.append("  • Sin gastos no esenciales.")
            lineas.append(
                "  Total no esenciales: "
                f"{formatear_monto(self.monto_gastos_no_esenciales)}"
            )

        return "\n".join(lineas)
