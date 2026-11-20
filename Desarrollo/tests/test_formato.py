from datetime import date, datetime

from utils.formato import formatear_fecha, formatear_monto


def test_formatear_monto():
    assert formatear_monto(0) == "$0,00"
    assert formatear_monto(1500.5) == "$1.500,50"
    assert formatear_monto(1234567.89) == "$1.234.567,89"
    assert formatear_monto(-1500.5) == "-$1.500,50"


def test_formatear_fecha():
    assert formatear_fecha("2026-11-20") == "20.11.26"
    assert formatear_fecha(date(2026, 1, 5)) == "05.01.26"
    assert formatear_fecha(datetime(2026, 11, 20, 13, 0)) == "20.11.26"
    assert formatear_fecha("sin-fecha") == "sin-fecha"
