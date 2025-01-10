import asyncio
import os
import sqlite3
from collections.abc import Callable, Coroutine, Sequence
from functools import wraps
from itertools import count
from typing import Any, Optional, TypeVar, cast

import aiosqlite
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
from tortoise.connection import connections
from tortoise.contrib.sqlite.regex import (
    install_regexp_functions as install_regexp_functions_to_db,
)
from tortoise.exceptions import (
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

T = TypeVar("T")
FuncType = Callable[..., Coroutine[None, None, T]]


def translate_exceptions(func: FuncType) -> FuncType:
    @wraps(func)
    async def translate_exceptions_(self, query, *args) -> T:
        try:
            return await func(self, query, *args)
        except sqlite3.OperationalError as exc:
            raise OperationalError(exc)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(exc)

    return translate_exceptions_


class SqliteClient(BaseDBAsyncClient):
    executor_class = SqliteExecutor
    query_class = SQLLiteQuery
    schema_generator = SqliteSchemaGenerator
    capabilities = Capabilities(
        "sqlite",
        daemon=False,
        requires_limit=True,
        inline_comment=True,
        support_for_update=False,
        support_update_limit_order_by=False,
    )

    def __init__(self, file_path: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.filename = file_path

        self.pragmas = kwargs.copy()
        self.pragmas.pop("connection_name", None)
        self.pragmas.pop("fetch_inserted", None)
        self.pragmas.setdefault("journal_mode", "WAL")
        self.pragmas.setdefault("journal_size_limit", 16384)
        self.pragmas.setdefault("foreign_keys", "ON")

        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def create_connection(self, with_db: bool) -> None:
        if not self._connection:  # pragma: no branch
            self._connection = aiosqlite.connect(self.filename, isolation_level=None)
            self._connection.start()
            await self._connection._connect()
            self._connection._conn.row_factory = sqlite3.Row
            for pragma, val in self.pragmas.items():
                cursor = await self._connection.execute(f"PRAGMA {pragma}={val}")
                await cursor.close()
            self.log.debug(
                "Created connection %s with params: filename=%s %s",
                self._connection,
                self.filename,
                " ".join(f"{k}={v}" for k, v in self.pragmas.items()),
            )

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self.log.debug(
                "Closed connection %s with params: filename=%s %s",
                self._connection,
                self.filename,
                " ".join(f"{k}={v}" for k, v in self.pragmas.items()),
            )

            self._connection = None

    async def db_create(self) -> None:
        # DB's are automatically created once accessed
        pass

    async def db_delete(self) -> None:
        await self.close()
        try:
            os.remove(self.filename)
        except FileNotFoundError:  # pragma: nocoverage
            pass
        except OSError as e:
            if e.errno != 22:  # fix: "sqlite://:memory:" in Windows
                raise e

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._lock, self)

    def _in_transaction(self) -> "TransactionContext":
        return SqliteTransactionContext(SqliteTransactionWrapper(self), self._lock)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            return (await connection.execute_insert(query, values))[0]

    @translate_exceptions
    async def execute_many(self, query: str, values: list[list]) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # This code is only ever called in AUTOCOMMIT mode
            await connection.execute("BEGIN")
            try:
                await connection.executemany(query, values)
            except Exception:
                await connection.rollback()
                raise
            else:
                await connection.commit()

    @translate_exceptions
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> tuple[int, Sequence[dict]]:
        query = query.replace("\x00", "'||CHAR(0)||'")
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            start = connection.total_changes
            rows = await connection.execute_fetchall(query, values)
            return (connection.total_changes - start) or len(rows), rows

    @translate_exceptions
    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> list[dict]:
        query = query.replace("\x00", "'||CHAR(0)||'")
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            return list(map(dict, await connection.execute_fetchall(query, values)))

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            await connection.executescript(query)


class SqliteTransactionContext(TransactionContext):
    """A SQLite-specific transaction context.

    SQLite uses a single connection, meaning that transactions need to
    acquire an exclusive lock on the connection to prevent other operations
    from interfering with the transaction. This is done by acquiring a lock
    on the connection object itself.
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
        self.token = connections.set(self.connection_name, self.connection)
        await self.connection.begin()
        return self.connection

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            if not self.connection._finalized:
                if exc_type:
                    # Can't rollback a transaction that already failed.
                    if exc_type is not TransactionManagementError:
                        await self.connection.rollback()
                else:
                    await self.connection.commit()
        finally:
            connections.reset(self.token)
            self._trxlock.release()


class SqliteTransactionWrapper(SqliteClient, TransactionalDBClient):
    def __init__(self, connection: SqliteClient) -> None:
        self.capabilities = connection.capabilities
        self.connection_name = connection.connection_name
        self._connection: aiosqlite.Connection = cast(aiosqlite.Connection, connection._connection)
        self._lock = asyncio.Lock()
        self._savepoint: Optional[str] = None
        self.log = connection.log
        self._finalized = False
        self.fetch_inserted = connection.fetch_inserted
        self._parent = connection

    def _in_transaction(self) -> "TransactionContext":
        return NestedTransactionContext(SqliteTransactionWrapper(self))

    @translate_exceptions
    async def execute_many(self, query: str, values: list[list]) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # Already within transaction, so ideal for performance
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


class SqliteClientWithRegexpSupport(SqliteClient):
    capabilities = Capabilities(
        "sqlite",
        daemon=False,
        requires_limit=True,
        inline_comment=True,
        support_for_update=False,
        support_for_posix_regex_queries=True,
    )

    async def create_connection(self, with_db: bool) -> None:
        await super().create_connection(with_db)
        if self._connection:
            await install_regexp_functions_to_db(self._connection)
