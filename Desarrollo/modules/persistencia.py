"""Persistencia de PTB respaldada por la tabla ``sesion_estado``.

El bot es de un único usuario y se ejecuta en chats privados, por lo que
``user_id`` y ``chat_id`` coinciden. El estado de la conversación se guarda en
``estado_actual`` y los datos de ``context.user_data`` (por ejemplo, el
borrador del comprobante) en ``contexto_json``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from telegram.ext import BasePersistence, PersistenceInput

from database import db


def _deserializar_estado(valor: str) -> Any:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return valor


class SQLitePersistence(BasePersistence):
    def __init__(
        self,
        db_path: str | Path | None = None,
        store_data: PersistenceInput | None = None,
    ) -> None:
        super().__init__(
            store_data=store_data
            or PersistenceInput(
                bot_data=False,
                chat_data=False,
                user_data=True,
                callback_data=False,
            )
        )
        self.db_path = db_path

    # ------------------------------------------------------------------ #
    # Conversaciones
    # ------------------------------------------------------------------ #

    async def get_conversations(self, name: str) -> dict[tuple[int, int], Any]:
        filas = db.listar_estados(nombre_conversacion=name, db_path=self.db_path)
        resultado: dict[tuple[int, int], Any] = {}
        for fila in filas:
            estado = fila.get("estado_actual") or ""
            if not estado:
                continue
            chat_id = int(fila["chat_id"])
            resultado[(chat_id, chat_id)] = _deserializar_estado(estado)
        return resultado

    async def update_conversation(
        self,
        name: str,
        key: tuple[int, ...],
        new_state: Any | None,
    ) -> None:
        chat_id = int(key[0])
        if new_state is None:
            db.eliminar_estado(chat_id, self.db_path)
            return

        existente = db.obtener_estado(chat_id, self.db_path)
        contexto = existente["contexto"] if existente else None
        db.guardar_estado(
            chat_id=chat_id,
            estado_actual=str(new_state),
            contexto=contexto,
            nombre_conversacion=name,
            db_path=self.db_path,
        )

    # ------------------------------------------------------------------ #
    # Datos de usuario
    # ------------------------------------------------------------------ #

    async def get_user_data(self) -> dict[int, Any]:
        filas = db.listar_estados(db_path=self.db_path)
        return {
            int(fila["chat_id"]): fila["contexto"]
            for fila in filas
            if fila.get("contexto") is not None
        }

    async def update_user_data(self, user_id: int, data: Any) -> None:
        chat_id = int(user_id)
        existente = db.obtener_estado(chat_id, self.db_path)

        if existente is None:
            if not data:
                return
            db.guardar_estado(
                chat_id=chat_id,
                estado_actual="",
                contexto=data,
                nombre_conversacion="comprobante",
                db_path=self.db_path,
            )
            return

        estado = existente.get("estado_actual") or ""
        if not estado and not data:
            db.eliminar_estado(chat_id, self.db_path)
            return

        db.guardar_estado(
            chat_id=chat_id,
            estado_actual=estado,
            contexto=data,
            nombre_conversacion=existente.get(
                "nombre_conversacion", "comprobante"
            ),
            db_path=self.db_path,
        )

    async def drop_user_data(self, user_id: int) -> None:
        chat_id = int(user_id)
        existente = db.obtener_estado(chat_id, self.db_path)
        if existente is None:
            return
        estado = existente.get("estado_actual") or ""
        if not estado:
            db.eliminar_estado(chat_id, self.db_path)
            return
        db.guardar_estado(
            chat_id=chat_id,
            estado_actual=estado,
            contexto=None,
            nombre_conversacion=existente.get(
                "nombre_conversacion", "comprobante"
            ),
            db_path=self.db_path,
        )

    async def refresh_user_data(self, user_id: int, user_data: Any) -> None:
        # La copia en memoria es la fuente de verdad durante el proceso.
        return None

    # ------------------------------------------------------------------ #
    # Datos que no se persisten
    # ------------------------------------------------------------------ #

    async def get_chat_data(self) -> dict[int, Any]:
        return {}

    async def update_chat_data(self, chat_id: int, data: Any) -> None:
        return None

    async def drop_chat_data(self, chat_id: int) -> None:
        return None

    async def refresh_chat_data(self, chat_id: int, chat_data: Any) -> None:
        return None

    async def get_bot_data(self) -> Any:
        return {}

    async def update_bot_data(self, data: Any) -> None:
        return None

    async def refresh_bot_data(self, bot_data: Any) -> None:
        return None

    async def get_callback_data(self) -> Any | None:
        return None

    async def update_callback_data(self, data: Any) -> None:
        return None

    async def flush(self) -> None:
        return None
