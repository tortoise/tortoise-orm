from __future__ import annotations

import asyncio
import contextvars
import importlib
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from tortoise.backends.base.config_generator import expand_db_url
from tortoise.exceptions import ConfigurationError

if TYPE_CHECKING:
    from tortoise.backends.base.client import BaseDBAsyncClient

    DBConfigType = dict[str, Any]


@dataclass(slots=True)
class ConnectionToken:
    """
    Token for resetting connection storage modifications.

    Used by transactions to temporarily replace a connection with a transaction client,
    then restore the original connection when the transaction completes.
    """

    _handler: ConnectionHandler
    _alias: str
    _old_value: BaseDBAsyncClient | None
    _cv_token: contextvars.Token | None = field(default=None)
    _used: bool = field(default=False)


class ConnectionHandler:
    """
    Connection management for a single TortoiseContext.

    Each TortoiseContext owns its own ConnectionHandler instance with isolated storage.
    """

    def __init__(self) -> None:
        self._db_config: DBConfigType | None = None
        self._create_db: bool = False
        # Use ContextVar for task isolation within this handler instance.
        # This ensures transactions (which use .set()) are isolated to the task.
        self._storage_var: contextvars.ContextVar[dict[str, BaseDBAsyncClient]] = (
            contextvars.ContextVar(f"storage_{id(self)}", default={})
        )

    @property
    def _storage(self) -> dict[str, BaseDBAsyncClient]:
        """
        Internal storage for connections.
        We use a property to provide a dict-like interface while being backed by a ContextVar.
        """
        return self._get_storage()

    @_storage.setter
    def _storage(self, value: dict[str, BaseDBAsyncClient]) -> None:
        """Allow direct assignment to storage for legacy compatibility (and tests)."""
        self._storage_var.set(value)

    def _get_storage(self) -> dict[str, BaseDBAsyncClient]:
        """Get the connection storage dict for the current task context."""
        return self._storage_var.get()

    def _set_storage(self, new_storage: dict[str, BaseDBAsyncClient]) -> None:
        """Set the connection storage dict. Used for testing purposes."""
        self._storage = new_storage

    def _copy_storage(self) -> dict[str, BaseDBAsyncClient]:
        """Return a shallow copy of the storage."""
        return dict(self._get_storage())

    def _clear_storage(self) -> None:
        """Clear all connections from storage in the current context."""
        self._storage_var.set({})

    async def _init(self, db_config: DBConfigType, create_db: bool) -> None:
        if self._db_config is None:
            self._db_config = db_config
        else:
            self._db_config.update(db_config)
        self._create_db = create_db
        await self._init_connections()

    def _init_config(self, db_config: DBConfigType, create_db: bool = False) -> None:
        if self._db_config is None:
            self._db_config = db_config
        else:
            self._db_config.update(db_config)
        self._create_db = create_db

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

        If the connection's event loop has changed (e.g., in a test with a new event loop),
        the connection is transparently replaced with a fresh one and a
        :class:`TortoiseLoopSwitchWarning<tortoise.warnings.TortoiseLoopSwitchWarning>`
        is emitted.

        Used for accessing the low-level connection object
        (:class:`BaseDBAsyncClient<tortoise.backends.base.client.BaseDBAsyncClient>`) for the
        given alias.

        :param conn_alias: The alias for which the connection has to be fetched

        :raises ConfigurationError: If the connection alias does not exist.
        """
        storage = self._get_storage()
        try:
            conn = storage[conn_alias]
            if not conn._check_loop():
                from tortoise.warnings import TortoiseLoopSwitchWarning

                warnings.warn(
                    f"Tortoise connection '{conn_alias}' was created on a different "
                    f"event loop and will be reconnected. If this is expected (e.g., "
                    f"in tests), use tortoise_test_context() or suppress with: "
                    f"warnings.filterwarnings('ignore', "
                    f"category=TortoiseLoopSwitchWarning)",
                    TortoiseLoopSwitchWarning,
                    stacklevel=2,
                )
                conn = self._create_connection(conn_alias)
                storage[conn_alias] = conn
            return conn
        except KeyError:
            connection: BaseDBAsyncClient = self._create_connection(conn_alias)
            storage[conn_alias] = connection
            return connection

    def set(self, conn_alias: str, conn_obj: BaseDBAsyncClient) -> ConnectionToken:
        """
        Sets the given alias to the provided connection object for the current task.

        :param conn_alias: The alias to set the connection for.
        :param conn_obj: The connection object that needs to be set for this alias.

        :returns: A token that can be used to restore the previous context via reset().

        .. note::
            This method is primarily used by transactions to temporarily replace a connection
            with a transaction client. Call reset() with the returned token to restore the
            original connection when the transaction completes.
        """
        old_value = self._get_storage().get(conn_alias)
        storage_copy = self._copy_storage()
        storage_copy[conn_alias] = conn_obj
        cv_token = self._storage_var.set(storage_copy)
        return ConnectionToken(
            _handler=self, _alias=conn_alias, _old_value=old_value, _cv_token=cv_token
        )

    def discard(self, conn_alias: str) -> BaseDBAsyncClient | None:
        """
        Discards the given alias from the storage in the `current context`.

        :param conn_alias: The alias for which the connection object should be discarded.

        .. important::
            Make sure to have called ``conn.close()`` for the provided alias before calling
            this method else there would be a connection leak (dangling connection).
        """
        return self._get_storage().pop(conn_alias, None)

    def reset(self, token: ConnectionToken | None) -> None:
        """
        Reset the connection storage to the previous context state.

        Restores the connection state for all aliases to what it was before the set() call.

        :param token:
            The token returned by the set() method. Can be None (no-op).
        """
        if token is None:
            return

        if token._used:
            raise ValueError("Token has already been used")
        token._used = True

        if token._cv_token and isinstance(token._cv_token, contextvars.Token):
            self._storage_var.reset(token._cv_token)
        else:
            # Fallback when no ContextVar token (e.g., mock tokens in tests)
            storage = self._copy_storage()
            if token._old_value is None:
                storage.pop(token._alias, None)
            else:
                storage[token._alias] = token._old_value
            self._storage = storage

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
        # Handle case where connections were never initialized (e.g., init failed)
        if self._db_config is None:
            return
        tasks = [conn.close() for conn in self.all()]
        await asyncio.gather(*tasks)
        if discard:
            for alias in self.db_config:
                self.discard(alias)


class _ConnectionsProxy:
    """
    Simple delegator that forwards all operations to the current context's ConnectionHandler.

    This provides backward compatibility for code using the `connections` module-level singleton.
    All operations require an active TortoiseContext - if no context is active, a clear error is raised.

    .. deprecated::
        Direct use of `connections` is deprecated. Use `get_connection()` or `get_connections()` instead,
        or access connections through the context: `ctx.connections`.
    """

    def _get_handler(self) -> ConnectionHandler:
        """Get the ConnectionHandler from the current context."""
        from tortoise.context import require_context

        return require_context().connections

    def __getattr__(self, name: str):
        """Delegate attribute access to the current context's ConnectionHandler."""
        return getattr(self._get_handler(), name)

    # Properties must be explicit since __getattr__ doesn't intercept descriptor access
    @property
    def db_config(self) -> DBConfigType:
        """Return the DB config."""
        return self._get_handler().db_config


connections = _ConnectionsProxy()


def get_connection(alias: str) -> BaseDBAsyncClient:
    """
    Get a database connection by alias from the current context.

    This is a convenience function. Prefer accessing connections directly
    via context: `ctx.connections.get(alias)`

    :param alias: The connection alias (e.g., "default")
    :raises ConfigurationError: If no context is active or connection not found
    """
    from tortoise.context import require_context

    return require_context().connections.get(alias)


def get_connections() -> ConnectionHandler:
    """
    Get the ConnectionHandler from the current context.

    This is a convenience function. Prefer accessing connections directly
    via context: `ctx.connections`

    :raises ConfigurationError: If no context is active
    """
    from tortoise.context import require_context

    return require_context().connections
