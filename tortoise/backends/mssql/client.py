import asyncio
from functools import wraps
from typing import Any, Callable, List, Optional, SupportsInt, Tuple, TypeVar, Union

import asyncodbc
import pyodbc
from asyncodbc.cursor import Cursor
from pypika.dialects import MSSQLQuery

from tortoise.backends.base.client import (
    BaseTransactionWrapper,
    ConnectionWrapper,
    NestedTransactionPooledContext,
    PoolConnectionWrapper,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.backends.mssql.schema_generator import MSSQLSchemaGenerator
from tortoise.backends.odbc.client import ODBCClient
from tortoise.exceptions import IntegrityError, OperationalError, TransactionManagementError

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


def translate_exceptions(func: F) -> F:
    @wraps(func)
    async def translate_exceptions_(self, *args):
        try:
            return await func(self, *args)
        except (
            pyodbc.OperationalError,
            pyodbc.ProgrammingError,
            pyodbc.DataError,
            pyodbc.InternalError,
            pyodbc.NotSupportedError,
        ) as exc:
            raise OperationalError(exc)
        except pyodbc.IntegrityError as exc:
            raise IntegrityError(exc)

    return translate_exceptions_  # type: ignore


class MSSQLClient(ODBCClient):
    query_class = MSSQLQuery
    schema_generator = MSSQLSchemaGenerator

    def __init__(
        self,
        *,
        user: str,
        password: str,
        host: str,
        port: SupportsInt,
        driver: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.dsn = f"DRIVER={driver};SERVER={host},{port};UID={user};PWD={password};"

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self))

    @translate_exceptions
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> Tuple[int, List[dict]]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:  # type:Cursor
                if values:
                    await cursor.execute(query, values)
                else:
                    await cursor.execute(query)
                try:
                    rows = await cursor.fetchall()
                    if rows:
                        fields = [c[0] for c in cursor.description]
                        return cursor.rowcount, [dict(zip(fields, row)) for row in rows]
                except pyodbc.ProgrammingError:
                    pass
                return cursor.rowcount, []

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:  # type:Cursor
                await cursor.execute(query)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.execute(query, values)
                await cursor.execute("SELECT @@IDENTITY")
                return (await cursor.fetchone())[0]

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                try:
                    await cursor.executemany(query, values)
                except Exception:
                    await connection.rollback()
                    raise
                else:
                    await connection.commit()

    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        return (await self.execute_query(query, values))[1]


class TransactionWrapper(MSSQLClient, BaseTransactionWrapper):
    def __init__(self, connection: ODBCClient) -> None:
        self.connection_name = connection.connection_name
        self._connection: asyncodbc.Connection = connection._connection
        self._lock = asyncio.Lock()
        self._trxlock = asyncio.Lock()
        self.log = connection.log
        self._finalized: Optional[bool] = None
        self.fetch_inserted = connection.fetch_inserted
        self._parent = connection

    def _in_transaction(self) -> "TransactionContext":
        return NestedTransactionPooledContext(self)

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return ConnectionWrapper(self._lock, self)

    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.executemany(query, values)

    async def start(self) -> None:
        await self._connection.execute("BEGIN TRANSACTION")
        self._finalized = False

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        self._finalized = True

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        self._finalized = True
