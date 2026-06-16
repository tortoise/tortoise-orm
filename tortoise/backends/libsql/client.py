from __future__ import annotations

import asyncio
import datetime
import sqlite3
from collections.abc import Callable, Coroutine, Sequence
from decimal import Decimal
from functools import wraps
from itertools import count
from typing import Any, TypeVar, cast

import aiosqlite
import libsql
from pypika_tortoise import SQLLiteQuery

from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    Capabilities,
    ConnectionWrapper,
    NestedTransactionContext,
    T_conn,
    TransactionalDBClient,
    TransactionContext,
)
from tortoise.backends.sqlite.executor import SqliteExecutor
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator
from tortoise.connection import get_connections
from tortoise.exceptions import (
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

T = TypeVar("T")
FuncType = Callable[..., Coroutine[None, None, T]]

# ── Parameter conversion ──
# libsql doesn't support sqlite3.register_adapter, so we must convert
# Python types (datetime, Decimal) to types libsql accepts.

def _convert_param(value: Any) -> Any:
    """Convert a single parameter value to a libsql-compatible type."""
    if isinstance(value, datetime.datetime):
        return value.isoformat(" ")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, datetime.time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value  # libsql supports bytes as BLOB
    return value


def _convert_params(values: list | None) -> list | None:
    """Convert all parameter values to libsql-compatible types."""
    if values is None:
        return None
    return [_convert_param(v) for v in values]


def _convert_many_params(values: list[list]) -> list[list]:
    """Convert all parameter values in a batch to libsql-compatible types."""
    return [[_convert_param(v) for v in row] for row in values]


def translate_exceptions(func: FuncType) -> FuncType:
    @wraps(func)
    async def translate_exceptions_(self, query, *args) -> T:
        try:
            return await func(self, query, *args)
        except sqlite3.OperationalError as exc:
            raise OperationalError(exc)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(exc)
        except ValueError as exc:
            # libsql raises ValueError for UNIQUE constraint failures
            # instead of sqlite3.IntegrityError
            msg = str(exc)
            if "UNIQUE constraint" in msg or "constraint failed" in msg.lower():
                raise IntegrityError(exc)
            raise

    return translate_exceptions_


class LibsqlClient(BaseDBAsyncClient):
    """
    Async client for libsql/Turso databases.

    Uses aiosqlite's thread-based async bridge with libsql as the underlying
    connector instead of sqlite3. This enables:

    - Remote connections to Turso Cloud (libsql://host.turso.io)
    - Embedded replicas (local file + sync to remote)
    - All sqlite3-compatible SQL via the async interface

    Connection URL format:
        libsql://user:pass@host:port/database
        libsql://host.turso.io/database?auth_token=xxx

    Or via config:
        db_url = "libsql://my-db.turso.io"
        credentials = {
            "sync_url": "libsql://my-db.turso.io",
            "auth_token": "xxx",
            "file_path": ":memory:",  # or local file path
        }
    """

    executor_class = SqliteExecutor
    query_class = SQLLiteQuery
    schema_generator = SqliteSchemaGenerator
    capabilities = Capabilities(
        "libsql",
        daemon=True,  # Remote server is a daemon
        requires_limit=True,
        inline_comment=True,
        support_for_update=False,
        support_update_limit_order_by=False,
        can_rollback_ddl=True,
        support_returning=True,
    )

    def __init__(self, file_path: str = ":memory:", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.filename = file_path
        self.sync_url = kwargs.pop("sync_url", None)
        self.auth_token = kwargs.pop("auth_token", None)
        self.sync_interval = kwargs.pop("sync_interval", None)

        self.pragmas = kwargs.copy()
        self.pragmas.pop("connection_name", None)
        self.pragmas.pop("fetch_inserted", None)
        self.pragmas.setdefault("journal_mode", "WAL")
        self.pragmas.setdefault("journal_size_limit", 16384)
        self.pragmas.setdefault("foreign_keys", "ON")

        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    def _make_connector(self) -> Callable[[], libsql.Connection]:
        """Create a libsql connector callable for aiosqlite."""

        def connector() -> libsql.Connection:
            kwargs: dict[str, Any] = {}
            if self.sync_url:
                kwargs["sync_url"] = self.sync_url
            if self.auth_token:
                kwargs["auth_token"] = self.auth_token
            if self.sync_interval:
                kwargs["sync_interval"] = self.sync_interval

            conn = libsql.connect(self.filename, **kwargs)

            # Initial sync for embedded replicas
            if self.sync_url:
                try:
                    conn.sync()
                except Exception:
                    pass  # Remote may not exist yet

            return conn

        return connector

    async def create_connection(self, with_db: bool) -> None:
        if not self._connection:  # pragma: no branch
            connector = self._make_connector()
            self._connection = aiosqlite.Connection(connector, iter_chunk_size=64)
            await self._connection

            # Set row factory (libsql.Connection may not support row_factory assignment)
            try:
                self._connection._conn.row_factory = sqlite3.Row
            except (AttributeError, TypeError):
                pass  # libsql doesn't support row_factory, aiosqlite handles row conversion

            for pragma, val in self.pragmas.items():
                cursor = await self._connection.execute(f"PRAGMA {pragma}={val}")
                await cursor.close()
            await self._post_connect()
            self.log.debug(
                "Created libsql connection %s with params: filename=%s sync_url=%s %s",
                self._connection,
                self.filename,
                self.sync_url,
                " ".join(f"{k}={v}" for k, v in self.pragmas.items()),
            )

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self.log.debug(
                "Closed libsql connection %s with params: filename=%s sync_url=%s",
                self._connection,
                self.filename,
                self.sync_url,
            )
            self._connection = None

    async def db_create(self) -> None:
        # DB's are automatically created once accessed
        pass

    async def db_delete(self) -> None:
        await self.close()
        if self.filename != ":memory:" and self.filename:
            import os

            try:
                os.remove(self.filename)
            except FileNotFoundError:  # pragma: nocoverage
                pass

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._lock, self)

    def _in_transaction(self) -> TransactionContext:
        return LibsqlTransactionContext(LibsqlTransactionWrapper(self), self._lock)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            return (await connection.execute_insert(query, _convert_params(values)))[0]

    @translate_exceptions
    async def execute_many(self, query: str, values: list[list]) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            await connection.execute("BEGIN")
            try:
                await connection.executemany(query, _convert_many_params(values))
            except Exception:
                await connection.rollback()
                raise
            else:
                await connection.commit()

    @translate_exceptions
    async def execute_query(
        self, query: str, values: list | None = None
    ) -> tuple[int, Sequence[dict]]:
        query = query.replace("\x00", "'||CHAR(0)||'")
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            cursor = await connection.execute(query, _convert_params(values))
            # Get column names BEFORE fetchall (description may be cleared after)
            description = cursor.description
            rows_raw = await cursor.fetchall()
            
            # For SELECT: convert tuples to dicts
            # For INSERT/UPDATE/DELETE: use rowcount for affected rows
            if description:
                # SELECT query — convert rows to dicts
                col_names = [desc[0] for desc in description]
                rows: Sequence[dict] = [dict(zip(col_names, row)) for row in rows_raw]
                count = len(rows)
            else:
                # Non-SELECT query (UPDATE/DELETE/INSERT)
                rows = []
                count = cursor.rowcount
                if count < 0:
                    count = 0
            
            await cursor.close()
            return count, rows

    @translate_exceptions
    async def execute_query_dict(self, query: str, values: list | None = None) -> list[dict]:
        query = query.replace("\x00", "'||CHAR(0)||'")
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            cursor = await connection.execute(query, _convert_params(values))
            description = cursor.description
            rows_raw = await cursor.fetchall()
            await cursor.close()
            
            if description and rows_raw:
                col_names = [desc[0] for desc in description]
                return [dict(zip(col_names, row)) for row in rows_raw]
            return list(map(dict, rows_raw))

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            await connection.executescript(query)


class LibsqlTransactionContext(TransactionContext):
    """A libsql-specific transaction context.

    Same as SQLite — uses a single connection with exclusive lock.
    """

    __slots__ = ("connection", "connection_name", "token", "_trxlock")

    def __init__(self, connection: Any, trxlock: asyncio.Lock) -> None:
        self.connection = connection
        self.connection_name = connection.connection_name
        self._trxlock = trxlock

    async def ensure_connection(self) -> None:
        if not self.connection._connection:
            await self.connection._parent.create_connection(with_db=True)
            self.connection._connection = self.connection._parent._connection

    async def __aenter__(self) -> T_conn:
        await self._trxlock.acquire()
        await self.ensure_connection()
        self.token = get_connections().set(self.connection_name, self.connection)
        await self.connection.begin()
        return self.connection

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            if not self.connection._finalized:
                if exc_type:
                    if exc_type is not TransactionManagementError:
                        await self.connection.rollback()
                else:
                    await self.connection.commit()
        finally:
            get_connections().reset(self.token)
            self._trxlock.release()


class LibsqlTransactionWrapper(LibsqlClient, TransactionalDBClient):
    def __init__(self, connection: LibsqlClient) -> None:
        self.capabilities = connection.capabilities
        self.connection_name = connection.connection_name
        self._connection: aiosqlite.Connection = cast(aiosqlite.Connection, connection._connection)
        self._lock = asyncio.Lock()
        self._savepoint: str | None = None
        self.log = connection.log
        self._finalized = False
        self.fetch_inserted = connection.fetch_inserted
        self._parent = connection

    def _in_transaction(self) -> TransactionContext:
        return NestedTransactionContext(LibsqlTransactionWrapper(self))

    @translate_exceptions
    async def execute_many(self, query: str, values: list[list]) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            await connection.executemany(query, values)

    async def begin(self) -> None:
        try:
            await self._connection.commit()
            await self._connection.execute("BEGIN")
        except sqlite3.OperationalError as exc:  # pragma: nocoverage
            raise TransactionManagementError(exc)

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        self._finalized = True

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        self._finalized = True

    async def savepoint(self) -> None:
        self._savepoint = _gen_savepoint_name()
        await self._connection.execute(f"SAVEPOINT {self._savepoint}")

    async def savepoint_rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if self._savepoint is None:
            raise TransactionManagementError("No savepoint to rollback to")
        await self._connection.execute(f"ROLLBACK TO {self._savepoint}")
        self._savepoint = None

    async def release_savepoint(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if self._savepoint is None:
            raise TransactionManagementError("No savepoint to rollback to")
        await self._connection.execute(f"RELEASE {self._savepoint}")


def _gen_savepoint_name(_c=count()) -> str:
    return f"tortoise_savepoint_{next(_c)}"
