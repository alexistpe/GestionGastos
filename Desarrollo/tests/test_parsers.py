import pytest

from utils import parsers
from utils.parsers import ErrorParseo


def test_normalizar_texto():
    assert parsers.normalizar_texto("  Peluquería  ") == "peluqueria"
    assert parsers.normalizar_texto("Tarjeta   Crédito") == "tarjeta credito"


def test_normalizar_nombre_etiqueta():
    assert parsers.normalizar_nombre_etiqueta("  Peluquería  ") == "peluqueria"
    assert parsers.normalizar_nombre_etiqueta("Tarjeta Crédito") == "tarjeta_credito"
    assert parsers.normalizar_nombre_etiqueta("  Gym!!  ") == "gym"

    with pytest.raises(ErrorParseo):
        parsers.normalizar_nombre_etiqueta("   ")
    with pytest.raises(ErrorParseo):
        parsers.normalizar_nombre_etiqueta("!!!")


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("15000", 15000.0),
        ("15.000", 15000.0),
        ("15.000,50", 15000.5),
        ("$15.000,50", 15000.5),
        ("$ 15.000", 15000.0),
        ("15,50", 15.5),
        ("1.234.567", 1234567.0),
        ("1,234.56", 1234.56),
        ("1,234,567", 1234567.0),
        ("ARS 25.000", 25000.0),
        ("25.000 pesos", 25000.0),
        ("0,5", 0.5),
    ],
)
def test_parsear_monto(texto, esperado):
    assert parsers.parsear_monto(texto) == pytest.approx(esperado)


@pytest.mark.parametrize("texto", ["", "abc", "0", "-5", "1e3", "0,00"])
def test_parsear_monto_invalido(texto):
    with pytest.raises(ErrorParseo):
        parsers.parsear_monto(texto)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("20.11.26", "2026-11-20"),
        ("20.11.2026", "2026-11-20"),
        ("2026-11-20", "2026-11-20"),
        ("20/11/26", "2026-11-20"),
        ("20-11-26", "2026-11-20"),
        ("1.1.26", "2026-01-01"),
    ],
)
def test_parsear_fecha(texto, esperado):
    assert parsers.parsear_fecha(texto) == esperado


@pytest.mark.parametrize(
    "texto", ["", "31.02.26", "2026-13-01", "foo", "20/13/26"]
)
def test_parsear_fecha_invalida(texto):
    with pytest.raises(ErrorParseo):
        parsers.parsear_fecha(texto)


def test_parsear_comando_balance():
    assert parsers.parsear_comando_balance("+ cuota 850000") == {
        "tipo": "balance",
        "signo": "+",
        "balance": "INGRESO",
        "etiqueta": "cuota",
        "monto": 850000.0,
    }

    egreso = parsers.parsear_comando_balance("- nafta $15.000,50")
    assert egreso["balance"] == "EGRESO"
    assert egreso["etiqueta"] == "nafta"
    assert egreso["monto"] == pytest.approx(15000.5)

    pegado = parsers.parsear_comando_balance("+gym 5000")
    assert pegado["balance"] == "INGRESO"
    assert pegado["etiqueta"] == "gym"
    assert pegado["monto"] == 5000.0

    espaciado = parsers.parsear_comando_balance("  -  Peluquería   15.000 ")
    assert espaciado["etiqueta"] == "peluqueria"
    assert espaciado["monto"] == 15000.0

    assert parsers.parsear_comando_balance("hola") is None

    with pytest.raises(ErrorParseo):
        parsers.parsear_comando_balance("+ cuota")
    with pytest.raises(ErrorParseo):
        parsers.parsear_comando_balance("-")


def test_parsear_analisis():
    assert parsers.parsear_comando("analisis") == {
        "tipo": "analisis",
        "desde": None,
        "hasta": None,
    }
    assert parsers.parsear_comando("analisis 01.11.26") == {
        "tipo": "analisis",
        "desde": "2026-11-01",
        "hasta": None,
    }
    assert parsers.parsear_comando("/analisis 01.11.26 15.11.26") == {
        "tipo": "analisis",
        "desde": "2026-11-01",
        "hasta": "2026-11-15",
    }

    with pytest.raises(ErrorParseo):
        parsers.parsear_comando("analisis 15.11.26 01.11.26")
    with pytest.raises(ErrorParseo):
        parsers.parsear_comando("analisis foo")


def test_parsear_alerta():
    por_etiqueta = parsers.parsear_comando("alerta nafta 15000")
    assert por_etiqueta == {
        "tipo": "alerta",
        "subtipo": "ETIQUETA",
        "etiqueta": "nafta",
        "monto": 15000.0,
    }

    total = parsers.parsear_comando("alerta 100000")
    assert total == {
        "tipo": "alerta",
        "subtipo": "MONTO_TOTAL",
        "etiqueta": None,
        "monto": 100000.0,
    }

    con_barra = parsers.parsear_comando("/alerta nafta 15.000")
    assert con_barra["etiqueta"] == "nafta"
    assert con_barra["monto"] == 15000.0

    assert parsers.parsear_comando("alertas") == {"tipo": "listar_alertas"}

    with pytest.raises(ErrorParseo):
        parsers.parsear_comando("alerta")
    with pytest.raises(ErrorParseo):
        parsers.parsear_comando("alerta nafta")


def test_parsear_etiquetas():
    assert parsers.parsear_comando("etiqueta supermercado") == {
        "tipo": "crear_etiqueta",
        "nombre": "supermercado",
    }
    assert parsers.parsear_comando("etiqueta Tarjeta Crédito") == {
        "tipo": "crear_etiqueta",
        "nombre": "tarjeta_credito",
    }
    assert parsers.parsear_comando("etiquetas") == {"tipo": "listar_etiquetas"}
    assert parsers.parsear_comando("eliminar etiqueta supermercado") == {
        "tipo": "eliminar_etiqueta",
        "nombre": "supermercado",
    }

    with pytest.raises(ErrorParseo):
        parsers.parsear_comando("etiqueta")
    with pytest.raises(ErrorParseo):
        parsers.parsear_comando("eliminar etiqueta")


def test_parsear_editar_y_borrar():
    assert parsers.parsear_comando("editar") == {"tipo": "editar", "id": None}
    assert parsers.parsear_comando("editar 42") == {"tipo": "editar", "id": 42}
    assert parsers.parsear_comando("/editar #42") == {"tipo": "editar", "id": 42}
    assert parsers.parsear_comando("borrar") == {"tipo": "borrar", "id": None}
    assert parsers.parsear_comando("borrar 7") == {"tipo": "borrar", "id": 7}

    with pytest.raises(ErrorParseo):
        parsers.parsear_comando("editar abc")
    with pytest.raises(ErrorParseo):
        parsers.parsear_comando("borrar 42 extra")


def test_comando_desconocido_y_mencion():
    assert parsers.parsear_comando("hola") is None
    assert parsers.parsear_comando("") is None
    assert parsers.parsear_comando("15.000") is None
    assert parsers.parsear_comando("/analisis@MiBot 01.11.26")["desde"] == "2026-11-01"


def test_extraer_etiqueta_de_caption():
    validas = ["nafta", "gym", "peluqueria", "tarjeta_credito"]

    assert parsers.extraer_etiqueta_de_caption("Nafta", validas) == "nafta"
    assert parsers.extraer_etiqueta_de_caption("etiqueta Nafta", validas) == "nafta"
    assert (
        parsers.extraer_etiqueta_de_caption("Peluquería", validas) == "peluqueria"
    )
    assert parsers.extraer_etiqueta_de_caption("etiqueta Tarjeta Crédito", validas) == (
        "tarjeta_credito"
    )
    assert parsers.extraer_etiqueta_de_caption("pago de nafta", validas) is None
    assert parsers.extraer_etiqueta_de_caption("", validas) is None
