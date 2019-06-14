import asyncio
import logging
import os
import sqlite3
from functools import wraps
from typing import List, Optional  # noqa

import aiosqlite

from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    BaseTransactionWrapper,
    Capabilities,
    ConnectionWrapper,
)
from tortoise.backends.sqlite.executor import SqliteExecutor
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator
from tortoise.exceptions import IntegrityError, OperationalError, TransactionManagementError


def translate_exceptions(func):
    @wraps(func)
    async def translate_exceptions_(self, query, *args):
        try:
            return await func(self, query, *args)
        except sqlite3.OperationalError as exc:
            raise OperationalError(exc)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(exc)

    return translate_exceptions_


class SqliteClient(BaseDBAsyncClient):
    executor_class = SqliteExecutor
    schema_generator = SqliteSchemaGenerator
    capabilities = Capabilities("sqlite", daemon=False, requires_limit=True, inline_comment=True)

    def __init__(self, file_path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.filename = file_path

        self.pragmas = kwargs.copy()
        self.pragmas.pop("connection_name", None)
        self.pragmas.pop("fetch_inserted", None)

        self._transaction_class = type(
            "TransactionWrapper", (TransactionWrapper, self.__class__), {}
        )
        self._connection = None  # type: Optional[aiosqlite.Connection]
        self._lock = asyncio.Lock()

    async def create_connection(self, with_db: bool) -> None:
        if not self._connection:  # pragma: no branch
            self._connection = aiosqlite.connect(self.filename, isolation_level=None)
            self._connection.start()
            await self._connection._connect()
            self._connection._conn.row_factory = sqlite3.Row
            for pragma, val in self.pragmas.items():
                cursor = await self._connection.execute("PRAGMA {}={}".format(pragma, val))
                await cursor.close()
            self.log.debug(
                "Created connection %s with params: filename=%s %s",
                self._connection,
                self.filename,
                " ".join(["{}={}".format(k, v) for k, v in self.pragmas.items()]),
            )

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self.log.debug(
                "Closed connection %s with params: filename=%s %s",
                self._connection,
                self.filename,
                " ".join(["{}={}".format(k, v) for k, v in self.pragmas.items()]),
            )
            self._connection = None

    async def db_create(self) -> None:
        pass

    async def db_delete(self) -> None:
        await self.close()
        try:
            os.remove(self.filename)
        except FileNotFoundError:  # pragma: nocoverage
            pass

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._connection, self._lock)

    def _in_transaction(self) -> "TransactionWrapper":
        return self._transaction_class(connection=self._connection, parent=self)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            return (await connection.execute_insert(query, values))[0]

    @translate_exceptions
    async def execute_many(self, query: str, values: List[list]) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Ensure that this is wrapped by a transaction, will provide a big speedup
            await connection.executemany(query, values)

    @translate_exceptions
    async def execute_query(self, query: str) -> List[dict]:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            res = [dict(row) for row in await connection.execute_fetchall(query)]
            return res

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            await connection.executescript(query)


class TransactionWrapper(BaseTransactionWrapper, SqliteClient):
    def __init__(self, connection: aiosqlite.Connection, parent: SqliteClient) -> None:
        self.connection_name = parent.connection_name
        self._connection = connection  # type: aiosqlite.Connection
        self._lock = parent._lock
        self.log = logging.getLogger("db_client")
        self._transaction_class = self.__class__
        self._old_context_value = None  # type: Optional[BaseDBAsyncClient]
        self._finalized = False
        self.fetch_inserted = parent.fetch_inserted
        self._current_transaction = parent._current_transaction
        self.parent = parent

    async def start(self) -> None:
        try:
            await self._connection.commit()
            await self._connection.execute("BEGIN")
        except sqlite3.OperationalError as exc:  # pragma: nocoverage
            raise TransactionManagementError(exc) from exc
        self._old_context_value = self._current_transaction.get()
        self._current_transaction.set(self)

    async def finalize(self) -> None:
        if not self._old_context_value:
            raise OperationalError("Finalize was called before transaction start")
        self._finalized = True
        self._current_transaction.set(self._old_context_value)

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        await self.finalize()

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        await self.finalize()
