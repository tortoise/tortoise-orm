import asyncio
from abc import ABC
from functools import wraps
from typing import Any, Callable, List, Optional, Tuple, TypeVar, Union

import asyncodbc
import pyodbc

from tortoise import BaseDBAsyncClient
from tortoise.backends.base.client import (
    BaseTransactionWrapper,
    ConnectionWrapper,
    NestedTransactionPooledContext,
    PoolConnectionWrapper,
    TransactionContext,
)
from tortoise.backends.odbc.executor import ODBCExecutor
from tortoise.exceptions import (
    DBConnectionError,
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

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
            pyodbc.InterfaceError,
        ) as exc:
            raise OperationalError(exc)
        except (pyodbc.IntegrityError, pyodbc.Error) as exc:
            raise IntegrityError(exc)

    return translate_exceptions_  # type: ignore


class ODBCClient(BaseDBAsyncClient, ABC):
    executor_class = ODBCExecutor

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._kwargs = kwargs.copy()
        self._kwargs.pop("connection_name", None)
        self._kwargs.pop("fetch_inserted", None)
        self.database = self._kwargs.pop("database", None)
        self.minsize = self._kwargs.pop("minsize", 1)
        self.maxsize = self._kwargs.pop("maxsize", 10)
        self.pool_recycle = self._kwargs.pop("pool_recycle", -1)
        self.echo = self._kwargs.pop("echo", False)
        self.dsn: Optional[str] = None

        self._template: dict = {}
        self._pool: Optional[asyncodbc.Pool] = None
        self._connection = None

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "minsize": self.minsize,
            "maxsize": self.maxsize,
            "echo": self.echo,
            "pool_recycle": self.pool_recycle,
            "dsn": self.dsn,
            "autocommit": True,
            **self._kwargs,
        }
        if with_db:
            self._template["database"] = self.database
        try:
            self._pool = await asyncodbc.create_pool(
                **self._template,
            )
            self.log.debug("Created connection %s pool with params: %s", self._pool, self._template)
        except pyodbc.InterfaceError:
            raise DBConnectionError(f"Can't establish connection to database {self.database}")

    async def _expire_connections(self) -> None:
        if self._pool:  # pragma: nobranch
            for conn in self._pool._free:
                conn._expired = True

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f"CREATE DATABASE {self.database}")
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f"DROP DATABASE {self.database}")
        await self.close()

    async def close(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self.log.debug("Closed connection %s with params: %s", self._connection, self._template)
            self._pool = None

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return PoolConnectionWrapper(self)

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                try:
                    await cursor.executemany(query, values)
                except Exception:
                    await cursor.rollback()
                    raise
                else:
                    await cursor.commit()

    @translate_exceptions
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> Tuple[int, List[dict]]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                if values:
                    await cursor.execute(query, values)
                else:
                    await cursor.execute(query)
                if query.startswith("UPDATE") or query.startswith("DELETE"):
                    return cursor.rowcount, []
                try:
                    rows = await cursor.fetchall()
                except pyodbc.ProgrammingError:
                    return cursor.rowcount, []
                if rows:
                    fields = [c[0] for c in cursor.description]
                    return cursor.rowcount, [dict(zip(fields, row)) for row in rows]
                return cursor.rowcount, []

    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        return (await self.execute_query(query, values))[1]

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:
                await cursor.execute(query)


class ODBCTransactionWrapper(BaseTransactionWrapper):
    def __init__(self, connection: ODBCClient) -> None:
        self.database = connection.database
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

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            cursor = await connection.cursor()
            await cursor.executemany(query, values)

    async def start(self) -> None:
        self._finalized = False
        self._connection._conn.autocommit = False

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        self._finalized = True
        self._connection._conn.autocommit = True

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        self._finalized = True
        self._connection._conn.autocommit = True
