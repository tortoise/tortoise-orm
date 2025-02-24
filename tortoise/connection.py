from __future__ import annotations

import asyncio
import contextvars
import importlib
from contextvars import ContextVar
from copy import copy
from typing import TYPE_CHECKING, Any

from tortoise.backends.base.config_generator import expand_db_url
from tortoise.exceptions import ConfigurationError

if TYPE_CHECKING:
    from tortoise.backends.base.client import BaseDBAsyncClient

    DBConfigType = dict[str, Any]


class ConnectionHandler:
    _conn_storage: ContextVar[dict[str, BaseDBAsyncClient]] = contextvars.ContextVar(
        "_conn_storage", default={}
    )

    def __init__(self) -> None:
        """Unified connection management interface."""
        self._db_config: DBConfigType | None = None
        self._create_db: bool = False

    async def _init(self, db_config: DBConfigType, create_db: bool) -> None:
        if self._db_config is None:
            self._db_config = db_config
        else:
            self._db_config.update(db_config)
        self._create_db = create_db
        await self._init_connections()

    @property
    def db_config(self) -> DBConfigType:
        """
        Return the DB config.

        This is the same config passed to the
        :meth:`Tortoise.init<tortoise.Tortoise.init>` method while initialization.

        :raises ConfigurationError:
            If this property is accessed before calling the
            :meth:`Tortoise.init<tortoise.Tortoise.init>` method.
        """
        if self._db_config is None:
            raise ConfigurationError(
                "DB configuration not initialised. Make sure to call "
                "Tortoise.init with a valid configuration before attempting "
                "to create connections."
            )
        return self._db_config

    def _get_storage(self) -> dict[str, BaseDBAsyncClient]:
        return self._conn_storage.get()

    def _set_storage(self, new_storage: dict[str, BaseDBAsyncClient]) -> contextvars.Token:
        # Should be used only for testing purposes.
        return self._conn_storage.set(new_storage)

    def _copy_storage(self) -> dict[str, BaseDBAsyncClient]:
        return copy(self._get_storage())

    def _clear_storage(self) -> None:
        self._get_storage().clear()

    def _discover_client_class(self, db_info: dict) -> type[BaseDBAsyncClient]:
        # Let exception bubble up for transparency
        engine_str = db_info.get("engine", "")
        engine_module = importlib.import_module(engine_str)
        try:
            if hasattr(engine_module, "get_client_class"):
                client_class = engine_module.get_client_class(db_info)
            else:
                client_class = engine_module.client_class
        except AttributeError:
            raise ConfigurationError(
                f'Backend for engine "{engine_str}" does not implement db client'
            )
        return client_class

    def _get_db_info(self, conn_alias: str) -> str | dict:
        try:
            return self.db_config[conn_alias]
        except KeyError:
            raise ConfigurationError(
                f"Unable to get db settings for alias '{conn_alias}'. Please "
                f"check if the config dict contains this alias and try again"
            )

    async def _init_connections(self) -> None:
        for alias in self.db_config:
            connection: BaseDBAsyncClient = self.get(alias)
            if self._create_db:
                await connection.db_create()

    def _create_connection(self, conn_alias: str) -> BaseDBAsyncClient:
        db_info = self._get_db_info(conn_alias)
        if isinstance(db_info, str):
            db_info = expand_db_url(db_info)
        client_class = self._discover_client_class(db_info)
        db_params = db_info["credentials"].copy()
        db_params.update({"connection_name": conn_alias})
        connection: BaseDBAsyncClient = client_class(**db_params)
        return connection

    def get(self, conn_alias: str) -> BaseDBAsyncClient:
        """
        Return the connection object for the given alias, creating it if needed.

        Used for accessing the low-level connection object
        (:class:`BaseDBAsyncClient<tortoise.backends.base.client.BaseDBAsyncClient>`) for the
        given alias.

        :param conn_alias: The alias for which the connection has to be fetched

        :raises ConfigurationError: If the connection alias does not exist.
        """
        storage: dict[str, BaseDBAsyncClient] = self._get_storage()
        try:
            return storage[conn_alias]
        except KeyError:
            connection: BaseDBAsyncClient = self._create_connection(conn_alias)
            storage[conn_alias] = connection
            return connection

    def set(self, conn_alias: str, conn_obj: BaseDBAsyncClient) -> contextvars.Token:
        """
        Sets the given alias to the provided connection object.

        :param conn_alias: The alias to set the connection for.
        :param conn_obj: The connection object that needs to be set for this alias.

        .. note::
            This method copies the storage from the `current context`, updates the
            ``conn_alias`` with the provided ``conn_obj`` and sets the updated storage
            in a `new context` and therefore returns a ``contextvars.Token`` in order to restore
            the original context storage.
        """
        storage_copy = self._copy_storage()
        storage_copy[conn_alias] = conn_obj
        return self._conn_storage.set(storage_copy)

    def discard(self, conn_alias: str) -> BaseDBAsyncClient | None:
        """
        Discards the given alias from the storage in the `current context`.

        :param conn_alias: The alias for which the connection object should be discarded.

        .. important::
            Make sure to have called ``conn.close()`` for the provided alias before calling
            this method else there would be a connection leak (dangling connection).
        """
        return self._get_storage().pop(conn_alias, None)

    def reset(self, token: contextvars.Token) -> None:
        """
        Reset the underlying storage to the previous context state.

        Resets the storage state to the `context` associated with the provided token. After
        resetting storage state, any additional `connections` created in the `old context` are
        copied into the `current context`.

        :param token:
            The token corresponding to the `context` to which the storage state has to
            be reset. Typically, this token is obtained by calling the
            :meth:`set<tortoise.connection.ConnectionHandler.set>` method of this class.
        """
        current_storage = self._get_storage()
        self._conn_storage.reset(token)
        prev_storage = self._get_storage()
        for alias, conn in current_storage.items():
            if alias not in prev_storage:
                prev_storage[alias] = conn

    def all(self) -> list[BaseDBAsyncClient]:
        """Returns a list of connection objects from the storage in the `current context`."""
        # The reason this method iterates over db_config and not over `storage` directly is
        # because: assume that someone calls `discard` with a certain alias, and calls this
        # method subsequently. The alias which just got discarded from the storage would not
        # appear in the returned list though it exists as part of the `db_config`.
        return [self.get(alias) for alias in self.db_config]

    async def close_all(self, discard: bool = True) -> None:
        """
        Closes all connections in the storage in the `current context`.

        All closed connections will be removed from the storage by default.

        :param discard:
            If ``False``, all connection objects are closed but `retained` in the storage.
        """
        tasks = [conn.close() for conn in self.all()]
        await asyncio.gather(*tasks)
        if discard:
            for alias in self.db_config:
                self.discard(alias)


connections = ConnectionHandler()
