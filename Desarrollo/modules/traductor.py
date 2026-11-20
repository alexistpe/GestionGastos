"""Traducción de comprobantes (imagen/PDF) a datos estructurados con Gemini.

La dependencia ``google-genai`` se importa de forma diferida para que el resto
del proyecto pueda usarse sin ella (por ejemplo, en tests de la capa de datos).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import config
from utils import parsers
from utils.parsers import ErrorParseo

logger = logging.getLogger(__name__)


class ErrorTraduccion(Exception):
    """Error de extracción con un mensaje apto para el usuario."""


MIME_TIPOS = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

INSTRUCCION_SISTEMA = (
    "Sos un asistente experto en lectura de comprobantes de pago argentinos. "
    "Extraés datos con precisión y no inventás información. "
    "Respondés únicamente con JSON válido, sin explicaciones."
)

ESQUEMA_RESPUESTA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "fecha": {
            "type": "string",
            "nullable": True,
            "description": "Fecha de la operación en formato YYYY-MM-DD.",
        },
        "destino": {
            "type": "string",
            "nullable": True,
            "description": "Comercio, persona o descripción breve de la operación.",
        },
        "monto": {
            "type": "number",
            "nullable": True,
            "description": "Monto total de la operación, siempre positivo.",
        },
        "balance": {
            "type": "string",
            "enum": ["INGRESO", "EGRESO"],
            "nullable": True,
            "description": (
                "INGRESO si el dinero entra a la cuenta del usuario; "
                "EGRESO si sale. null si no es concluyente."
            ),
        },
        "moneda": {
            "type": "string",
            "nullable": True,
            "description": "Código ISO de la moneda, por ejemplo ARS.",
        },
    },
    "required": ["fecha", "destino", "monto", "balance", "moneda"],
}


@dataclass
class ComprobanteExtraido:
    fecha: str | None
    destino: str | None
    monto: float | None
    balance: str | None
    moneda: str = "ARS"
    advertencias: list[str] = field(default_factory=list)

    def a_dict(self) -> dict[str, Any]:
        return {
            "fecha": self.fecha,
            "destino": self.destino,
            "monto": self.monto,
            "balance": self.balance,
            "moneda": self.moneda,
            "advertencias": list(self.advertencias),
        }


class Traductor:
    """Wrapper de Gemini para convertir un comprobante en datos contables."""

    def __init__(
        self,
        api_key: str | None = None,
        modelo: str | None = None,
        cliente: Any | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = config.GEMINI_API_KEY if api_key is None else api_key
        self.modelo = modelo or config.GEMINI_MODEL
        self._cliente = cliente
        self.timeout = timeout

    def _obtener_cliente(self) -> Any:
        if self._cliente is not None:
            return self._cliente

        if not self.api_key:
            raise ErrorTraduccion(
                "Falta GEMINI_API_KEY. Configurala en el archivo .env."
            )

        try:
            from google import genai
        except ImportError as exc:
            raise ErrorTraduccion(
                "Falta la dependencia google-genai. "
                "Instalala con: pip install google-genai"
            ) from exc

        self._cliente = genai.Client(api_key=self.api_key)
        return self._cliente

    def _construir_prompt(self, contexto: str | None = None) -> str:
        prompt = (
            "Analizá el comprobante adjunto y devolvé un objeto JSON con estos "
            "campos:\n"
            "- fecha: fecha de la operación en formato YYYY-MM-DD o null.\n"
            "- destino: comercio, persona o descripción breve o null.\n"
            "- monto: monto total positivo, sin símbolos, o null.\n"
            "- balance: INGRESO si el dinero entra a la cuenta del usuario, "
            "EGRESO si sale, o null si no es concluyente.\n"
            "- moneda: código ISO de la moneda; si no se indica, usá ARS.\n\n"
            "No inventes datos. Si un dato no aparece en el comprobante, "
            "devolvé null. Respondé únicamente con el JSON."
        )
        if contexto and contexto.strip():
            prompt += (
                "\n\nTexto enviado por el usuario como contexto: "
                f"{contexto.strip()[:500]}"
            )
        return prompt

    async def _llamar_api(
        self, prompt: str, contenido: bytes, mime_type: str
    ) -> str:
        from google.genai import types

        cliente = self._obtener_cliente()
        configuracion = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=ESQUEMA_RESPUESTA,
            system_instruction=INSTRUCCION_SISTEMA,
        )
        respuesta = await cliente.aio.models.generate_content(
            model=self.modelo,
            contents=[
                types.Part.from_bytes(data=contenido, mime_type=mime_type),
                prompt,
            ],
            config=configuracion,
        )
        texto = getattr(respuesta, "text", None)
        if not texto or not str(texto).strip():
            raise ErrorTraduccion("La respuesta del servicio vino vacía.")
        return str(texto)

    async def _llamar_con_reintento(
        self, prompt: str, contenido: bytes, mime_type: str
    ) -> str:
        for intento in range(2):
            try:
                return await asyncio.wait_for(
                    self._llamar_api(prompt, contenido, mime_type),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError as exc:
                logger.warning(
                    "Gemini timeout: modelo=%s intento=%d",
                    self.modelo,
                    intento + 1,
                )
                if intento == 0:
                    continue
                raise ErrorTraduccion(
                    "El servicio tardó más de lo esperado. "
                    "Reintentá o ingresá el comprobante manualmente."
                ) from exc
            except ErrorTraduccion:
                raise
            except Exception as exc:
                logger.warning(
                    "Gemini error: modelo=%s tipo=%s",
                    self.modelo,
                    type(exc).__name__,
                )
                raise ErrorTraduccion(
                    "No se pudo procesar el comprobante. "
                    "Reintentá o ingresalo manualmente."
                ) from exc

        raise ErrorTraduccion("No se pudo procesar el comprobante.")

    def _parsear_respuesta(self, texto: str) -> dict[str, Any]:
        limpio = texto.strip()
        if limpio.startswith("```"):
            limpio = re.sub(
                r"^```(?:json)?\s*", "", limpio, flags=re.IGNORECASE
            )
            limpio = re.sub(r"\s*```$", "", limpio)

        try:
            datos = json.loads(limpio)
        except json.JSONDecodeError as exc:
            raise ErrorTraduccion(
                "El servicio devolvió una respuesta inválida. "
                "Reintentá o ingresá el comprobante manualmente."
            ) from exc

        if not isinstance(datos, dict):
            raise ErrorTraduccion("El servicio devolvió un formato inesperado.")

        if isinstance(datos.get("comprobante"), dict):
            datos = datos["comprobante"]

        return datos

    def _validar_extraccion(
        self, datos: dict[str, Any]
    ) -> ComprobanteExtraido:
        advertencias: list[str] = []

        fecha_raw = datos.get("fecha")
        fecha: str | None = None
        if fecha_raw:
            texto_fecha = str(fecha_raw).strip()
            if "T" in texto_fecha:
                texto_fecha = texto_fecha[:10]
            try:
                fecha = parsers.parsear_fecha(texto_fecha)
            except ErrorParseo:
                advertencias.append("No se pudo interpretar la fecha.")
        else:
            advertencias.append("No se pudo detectar la fecha.")

        monto_raw = datos.get("monto")
        monto: float | None = None
        if monto_raw is not None:
            if isinstance(monto_raw, (int, float)) and not isinstance(
                monto_raw, bool
            ):
                if float(monto_raw) > 0:
                    monto = float(monto_raw)
            else:
                try:
                    monto = parsers.parsear_monto(str(monto_raw))
                except ErrorParseo:
                    pass
            if monto is None:
                advertencias.append("No se pudo interpretar el monto.")
        else:
            advertencias.append("No se pudo detectar el monto.")

        balance_raw = datos.get("balance")
        balance: str | None = None
        if balance_raw is not None:
            balance = str(balance_raw).strip().upper()
            if balance not in ("INGRESO", "EGRESO"):
                balance = None
        if balance is None:
            advertencias.append("No se pudo determinar el balance.")

        destino_raw = datos.get("destino")
        destino: str | None = None
        if destino_raw is not None:
            texto_destino = str(destino_raw).strip()
            if texto_destino.lower() not in {"", "null", "none", "n/a"}:
                destino = texto_destino[:200] or None
        if destino is None:
            advertencias.append("No se pudo detectar el destino.")

        moneda_raw = datos.get("moneda")
        moneda = (
            str(moneda_raw).strip().upper() if moneda_raw else "ARS"
        ) or "ARS"
        if moneda.lower() in {"NULL", "NONE", "N/A"}:
            moneda = "ARS"

        return ComprobanteExtraido(
            fecha=fecha,
            destino=destino,
            monto=monto,
            balance=balance,
            moneda=moneda,
            advertencias=advertencias,
        )

    async def traducir_comprobante(
        self,
        contenido: bytes,
        mime_type: str,
        contexto: str | None = None,
    ) -> ComprobanteExtraido:
        if not contenido:
            raise ErrorTraduccion("El archivo del comprobante está vacío.")

        mime = (mime_type or "").split(";")[0].strip().lower()
        if mime == "image/jpg":
            mime = "image/jpeg"
        if mime not in MIME_TIPOS:
            raise ErrorTraduccion(
                "Formato no soportado. Enviá una imagen JPG/PNG/WEBP o un PDF."
            )

        logger.info("Gemini request: modelo=%s mime=%s", self.modelo, mime)
        prompt = self._construir_prompt(contexto)
        texto = await self._llamar_con_reintento(prompt, contenido, mime)
        datos = self._parsear_respuesta(texto)
        resultado = self._validar_extraccion(datos)
        logger.info(
            "Gemini ok: modelo=%s advertencias=%d",
            self.modelo,
            len(resultado.advertencias),
        )
        return resultado
