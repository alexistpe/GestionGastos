"""Configuración central del proyecto.

Las rutas relativas se resuelven contra el directorio de este archivo, de modo
que el proyecto funcione igual en Linux y en Termux.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _cargar_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(BASE_DIR / ".env")


_cargar_dotenv()


def _ruta_desde_entorno(nombre: str, por_defecto: Path) -> Path:
    valor = os.getenv(nombre, "").strip()
    if not valor:
        return por_defecto
    ruta = Path(valor).expanduser()
    return ruta if ruta.is_absolute() else BASE_DIR / ruta


DATA_DIR = _ruta_desde_entorno("DATA_DIR", BASE_DIR / "data")
LOG_DIR = _ruta_desde_entorno("LOG_DIR", BASE_DIR / "logs")
DB_PATH = _ruta_desde_entorno("DB_PATH", DATA_DIR / "gastos.db")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

_TELEGRAM_CHAT_ID_RAW = os.getenv("TELEGRAM_CHAT_ID", "").strip()
try:
    TELEGRAM_CHAT_ID: int | None = (
        int(_TELEGRAM_CHAT_ID_RAW) if _TELEGRAM_CHAT_ID_RAW else None
    )
except ValueError:
    TELEGRAM_CHAT_ID = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
ZONA_HORARIA = os.getenv("TZ", "America/Argentina/Buenos_Aires").strip()


def validar_config(
    requiere_telegram: bool = True, requiere_gemini: bool = True
) -> list[str]:
    """Devuelve la lista de variables obligatorias que faltan."""
    faltantes: list[str] = []
    if requiere_telegram:
        if not TELEGRAM_BOT_TOKEN:
            faltantes.append("TELEGRAM_BOT_TOKEN")
        if TELEGRAM_CHAT_ID is None:
            faltantes.append("TELEGRAM_CHAT_ID")
    if requiere_gemini and not GEMINI_API_KEY:
        faltantes.append("GEMINI_API_KEY")
    return faltantes
