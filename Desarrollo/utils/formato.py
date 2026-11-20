"""Formato de montos y fechas para los informes del bot."""

from __future__ import annotations

from datetime import date, datetime


def formatear_monto(monto: float) -> str:
    """Devuelve un monto en formato argentino, por ejemplo ``$15.000,50``."""
    valor = float(monto)
    signo = "-" if valor < 0 else ""
    texto = f"{abs(valor):,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{signo}${texto}"


def formatear_fecha(valor: date | datetime | str) -> str:
    """Devuelve una fecha como ``DD.MM.AA`` cuando es posible."""
    if isinstance(valor, datetime):
        valor = valor.date()
    if isinstance(valor, str):
        try:
            valor = date.fromisoformat(valor)
        except ValueError:
            return valor
    if isinstance(valor, date):
        return valor.strftime("%d.%m.%y")
    return str(valor)
