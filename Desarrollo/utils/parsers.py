"""Parsers de comandos, montos, fechas y etiquetas.

Las funciones devuelven diccionarios con un campo ``tipo`` cuando reconocen una
instrucción. Si el texto no corresponde a ningún comando devuelven ``None``.
Si el comando se reconoce pero los argumentos son inválidos, lanzan
``ErrorParseo`` con un mensaje listo para enviar al usuario.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date


class ErrorParseo(ValueError):
    """Error de sintaxis con un mensaje apto para el usuario."""


def normalizar_texto(texto: str) -> str:
    """Pasa a minúsculas, quita tildes y colapsa espacios."""
    if not isinstance(texto, str):
        raise ErrorParseo("El mensaje no es válido.")
    texto = texto.strip().lower()
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    return re.sub(r"\s+", " ", texto)


def normalizar_nombre_etiqueta(nombre: str) -> str:
    """Normaliza una etiqueta a ``[a-z0-9_]`` sin espacios ni tildes."""
    texto = normalizar_texto(nombre)
    texto = re.sub(r"\s+", "_", texto)
    texto = re.sub(r"[^a-z0-9_]", "", texto).strip("_")
    if not texto:
        raise ErrorParseo(
            "El nombre de la etiqueta no es válido. Usá letras, números o guiones bajos."
        )
    return texto


def _quitar_barra(texto: str) -> str:
    texto = texto.strip()
    if texto.startswith("/"):
        texto = texto[1:]
    return texto


def _quitar_mencion(texto: str) -> str:
    """Quita el ``@bot`` de un comando de Telegram."""
    return re.sub(r"^(\w+)@\w+", r"\1", texto, count=1)


def parsear_monto(texto: str) -> float:
    """Convierte un monto en formato argentino o internacional a float."""
    original = texto.strip()
    if not original:
        raise ErrorParseo("Falta el monto.")
    if "-" in original:
        raise ErrorParseo("El monto debe ser positivo.")

    limpio = original.lower().replace("ars", "").replace("pesos", "").replace("$", "")
    limite = re.search(r"[a-z]", limpio)
    if limite:
        raise ErrorParseo("Monto inválido.")

    limpio = re.sub(r"[^\d.,]", "", limpio)
    if not limpio:
        raise ErrorParseo("Monto inválido.")

    if "," in limpio and "." in limpio:
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        if limpio.count(",") > 1 and re.fullmatch(r"\d{1,3}(?:,\d{3})+", limpio):
            limpio = limpio.replace(",", "")
        else:
            limpio = limpio.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", limpio):
        limpio = limpio.replace(".", "")

    try:
        monto = float(limpio)
    except ValueError as exc:
        raise ErrorParseo("Monto inválido.") from exc

    if monto <= 0:
        raise ErrorParseo("El monto debe ser mayor que cero.")
    return monto


def parsear_fecha(texto: str) -> str:
    """Convierte fechas locales o ISO a ``YYYY-MM-DD``."""
    original = texto.strip()
    if not original:
        raise ErrorParseo("Falta la fecha.")

    coincidencia = re.fullmatch(
        r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", original
    )
    if coincidencia:
        dia = int(coincidencia.group(1))
        mes = int(coincidencia.group(2))
        anio_texto = coincidencia.group(3)
        anio = int(anio_texto)
        if len(anio_texto) == 2:
            anio += 2000
        try:
            return date(anio, mes, dia).isoformat()
        except ValueError as exc:
            raise ErrorParseo(f"Fecha inválida: {original}.") from exc

    coincidencia = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", original)
    if coincidencia:
        anio, mes, dia = (int(parte) for parte in coincidencia.groups())
        try:
            return date(anio, mes, dia).isoformat()
        except ValueError as exc:
            raise ErrorParseo(f"Fecha inválida: {original}.") from exc

    raise ErrorParseo("Fecha inválida. Usá DD.MM.AA o YYYY-MM-DD.")


def parsear_comando_balance(texto: str) -> dict | None:
    normalizado = normalizar_texto(_quitar_barra(texto))
    coincidencia = re.fullmatch(r"([+-])\s*([a-z0-9_]+)\s+(.+)", normalizado)
    if not coincidencia:
        if normalizado.startswith(("+", "-")):
            raise ErrorParseo(
                "Sintaxis de balance inválida. Usá: + etiqueta monto o - etiqueta monto."
            )
        return None

    signo, etiqueta, monto_texto = coincidencia.groups()
    return {
        "tipo": "balance",
        "signo": signo,
        "balance": "INGRESO" if signo == "+" else "EGRESO",
        "etiqueta": normalizar_nombre_etiqueta(etiqueta),
        "monto": parsear_monto(monto_texto),
    }


def parsear_analisis(texto: str) -> dict | None:
    normalizado = normalizar_texto(_quitar_barra(texto))
    coincidencia = re.fullmatch(r"analisis(?:\s+(.+))?", normalizado)
    if not coincidencia:
        return None

    resto = coincidencia.group(1)
    if not resto:
        return {"tipo": "analisis", "desde": None, "hasta": None}

    partes = resto.split()
    if len(partes) == 1:
        return {"tipo": "analisis", "desde": parsear_fecha(partes[0]), "hasta": None}
    if len(partes) == 2:
        desde = parsear_fecha(partes[0])
        hasta = parsear_fecha(partes[1])
        if desde > hasta:
            raise ErrorParseo("La fecha inicial no puede ser posterior a la final.")
        return {"tipo": "analisis", "desde": desde, "hasta": hasta}

    raise ErrorParseo(
        "Sintaxis de análisis inválida. Usá: analisis [DD.MM.AA [DD.MM.AA]]."
    )


def parsear_alerta(texto: str) -> dict | None:
    normalizado = normalizar_texto(_quitar_barra(texto))
    coincidencia = re.fullmatch(r"alerta(?:\s+(.+))?", normalizado)
    if not coincidencia:
        return None

    resto = coincidencia.group(1)
    if not resto:
        raise ErrorParseo(
            "Falta el monto. Usá: alerta etiqueta monto o alerta monto."
        )

    partes = resto.split()
    if len(partes) == 1:
        if re.search(r"[a-z]", partes[0]):
            raise ErrorParseo(
                "Falta el monto. Usá: alerta etiqueta monto o alerta monto."
            )
        return {
            "tipo": "alerta",
            "subtipo": "MONTO_TOTAL",
            "etiqueta": None,
            "monto": parsear_monto(partes[0]),
        }

    if len(partes) == 2:
        return {
            "tipo": "alerta",
            "subtipo": "ETIQUETA",
            "etiqueta": normalizar_nombre_etiqueta(partes[0]),
            "monto": parsear_monto(partes[1]),
        }

    raise ErrorParseo(
        "Sintaxis de alerta inválida. Usá: alerta etiqueta monto o alerta monto."
    )


def parsear_etiqueta(texto: str) -> dict | None:
    normalizado = normalizar_texto(_quitar_barra(texto))
    if normalizado == "etiquetas":
        return {"tipo": "listar_etiquetas"}

    coincidencia = re.fullmatch(r"etiqueta(?:\s+(.+))?", normalizado)
    if not coincidencia:
        return None

    resto = coincidencia.group(1)
    if not resto:
        raise ErrorParseo("Falta el nombre. Usá: etiqueta nombre.")

    return {
        "tipo": "crear_etiqueta",
        "nombre": normalizar_nombre_etiqueta(resto),
    }


def parsear_eliminar_etiqueta(texto: str) -> dict | None:
    normalizado = normalizar_texto(_quitar_barra(texto))
    coincidencia = re.fullmatch(r"eliminar\s+etiqueta(?:\s+(.+))?", normalizado)
    if not coincidencia:
        return None

    resto = coincidencia.group(1)
    if not resto:
        raise ErrorParseo("Falta el nombre. Usá: eliminar etiqueta nombre.")

    return {
        "tipo": "eliminar_etiqueta",
        "nombre": normalizar_nombre_etiqueta(resto),
    }


def _parsear_editar_borrar(texto: str, comando: str) -> dict | None:
    normalizado = normalizar_texto(_quitar_barra(texto))
    if normalizado == comando:
        return {"tipo": comando, "id": None}
    if not normalizado.startswith(comando + " "):
        return None

    resto = normalizado[len(comando) :].strip()
    coincidencia = re.fullmatch(r"#?(\d+)", resto)
    if not coincidencia:
        raise ErrorParseo(f"ID inválido. Usá: {comando} [ID].")
    return {"tipo": comando, "id": int(coincidencia.group(1))}


def parsear_comando(texto: str) -> dict | None:
    """Punto de entrada único para interpretar mensajes de texto."""
    if not texto or not texto.strip():
        return None

    normalizado = _quitar_mencion(normalizar_texto(_quitar_barra(texto)))

    for parser in (
        parsear_analisis,
        parsear_alerta,
        parsear_etiqueta,
        parsear_eliminar_etiqueta,
    ):
        resultado = parser(normalizado)
        if resultado is not None:
            return resultado

    if normalizado == "alertas":
        return {"tipo": "listar_alertas"}

    for comando in ("editar", "borrar"):
        resultado = _parsear_editar_borrar(normalizado, comando)
        if resultado is not None:
            return resultado

    return parsear_comando_balance(normalizado)


def extraer_etiqueta_de_caption(
    texto: str, etiquetas_validas: set[str] | list[str]
) -> str | None:
    """Devuelve la etiqueta indicada en el caption, si coincide con una válida."""
    if not texto or not texto.strip():
        return None

    validas = {normalizar_nombre_etiqueta(etiqueta) for etiqueta in etiquetas_validas}
    normalizado = normalizar_texto(texto)

    candidato = normalizar_nombre_etiqueta(normalizado)
    if candidato in validas:
        return candidato

    coincidencia = re.fullmatch(r"etiqueta\s+(.+)", normalizado)
    if coincidencia:
        candidato = normalizar_nombre_etiqueta(coincidencia.group(1))
        if candidato in validas:
            return candidato

    return None
