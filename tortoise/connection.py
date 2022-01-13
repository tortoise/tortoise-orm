import asyncio
import contextvars
import copy
import importlib
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from tortoise.backends.base.config_generator import expand_db_url
from tortoise.exceptions import ConfigurationError

if TYPE_CHECKING:
    from tortoise.backends.base.client import BaseDBAsyncClient

    DBConfigType = Dict[str, Any]


class ConnectionHandler:
    _conn_storage: ContextVar[Dict[str, "BaseDBAsyncClient"]] = contextvars.ContextVar(
        "_conn_storage", default={}
    )

    def __init__(self) -> None:
        self._db_config: Optional["DBConfigType"] = None
        self._create_db: bool = False

    async def _init(self, db_config: "DBConfigType", create_db: bool):
        self._db_config = db_config
        self._create_db = create_db
        await self._init_connections()

    @property
    def db_config(self) -> "DBConfigType":
        if self._db_config is None:
            raise ConfigurationError(
                "DB configuration not initialised. Make sure to call "
                "Tortoise.init with a valid configuration before attempting "
                "to create connections."
            )
        return self._db_config

    def _get_storage(self) -> Dict[str, "BaseDBAsyncClient"]:
        return self._conn_storage.get()

    def _copy_storage(self) -> Dict[str, "BaseDBAsyncClient"]:
        return copy.copy(self._get_storage())

    def _clear_storage(self) -> None:
        self._get_storage().clear()

    def _discover_client_class(self, engine: str) -> Type["BaseDBAsyncClient"]:
        # Let exception bubble up for transparency
        engine_module = importlib.import_module(engine)

        try:
            client_class = engine_module.client_class  # type: ignore
        except AttributeError:
            raise ConfigurationError(f'Backend for engine "{engine}" does not implement db client')
        return client_class

    def _get_db_info(self, conn_alias: str) -> Union[str, Dict]:
        try:
            return self.db_config[conn_alias]
        except KeyError:
            raise ConfigurationError(
                f"Unable to get db settings for alias '{conn_alias}'. Please "
                f"check if the config dict contains this alias and try again"
            )

    async def _init_connections(self) -> None:
        for alias in self.db_config:
            connection: "BaseDBAsyncClient" = self.get(alias)
            if self._create_db:
                await connection.db_create()

    def _create_connection(self, conn_alias: str) -> "BaseDBAsyncClient":
        db_info = self._get_db_info(conn_alias)
        if isinstance(db_info, str):
            db_info = expand_db_url(db_info)
        client_class = self._discover_client_class(db_info.get("engine", ""))
        db_params = db_info["credentials"].copy()
        db_params.update({"connection_name": conn_alias})
        connection: "BaseDBAsyncClient" = client_class(**db_params)
        return connection

    def get(self, conn_alias: str) -> "BaseDBAsyncClient":
        storage: Dict[str, "BaseDBAsyncClient"] = self._get_storage()
        try:
            return storage[conn_alias]
        except KeyError:
            connection: BaseDBAsyncClient = self._create_connection(conn_alias)
            storage[conn_alias] = connection
            return connection

    def _set_storage(self, new_storage: Dict[str, "BaseDBAsyncClient"]) -> contextvars.Token:
        # Should be used only for testing purposes.
        return self._conn_storage.set(new_storage)

    def set(self, conn_alias: str, conn) -> contextvars.Token:
        storage_copy = self._copy_storage()
        storage_copy[conn_alias] = conn
        return self._conn_storage.set(storage_copy)

    def discard(self, conn_alias: str) -> Optional["BaseDBAsyncClient"]:
        return self._get_storage().pop(conn_alias, None)

    def reset(self, token: contextvars.Token):
        current_storage = self._get_storage()
        self._conn_storage.reset(token)
        prev_storage = self._get_storage()
        for alias, conn in current_storage.items():
            if alias not in prev_storage:
                prev_storage[alias] = conn

    def all(self) -> List["BaseDBAsyncClient"]:
        # Returning a list here so as to avoid accidental
        # mutation of the underlying storage dict
        return list(self._get_storage().values())

    async def close_all(self, discard: bool = False) -> None:
        tasks = [conn.close() for conn in self._get_storage().values()]
        await asyncio.gather(*tasks)
        if discard:
            for alias in tuple(self._get_storage()):
                self.discard(alias)


connections = ConnectionHandler()
