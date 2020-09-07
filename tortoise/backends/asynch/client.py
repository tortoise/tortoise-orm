from functools import wraps
from typing import Any, Callable, List, Optional, Sequence, SupportsInt, Tuple, TypeVar, Union

from pypika import ClickHouseQuery

import asynch
from asynch import errors
from tortoise import BaseDBAsyncClient
from tortoise.backends.asynch.executor import AsynchExecutor
from tortoise.backends.asynch.schema_generator import AsynchSchemaGenerator
from tortoise.backends.base.client import (
    Capabilities,
    ConnectionWrapper,
    PoolConnectionWrapper,
    TransactionContext,
)
from tortoise.exceptions import DBConnectionError, IntegrityError, NotSupportError, OperationalError

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


def translate_exceptions(func: F) -> F:
    @wraps(func)
    async def translate_exceptions_(self, *args):
        try:
            return await func(self, *args)
        except (errors.ServerException,) as exc:
            raise OperationalError(exc)

    return translate_exceptions_  # type: ignore


class AsynchDBClient(BaseDBAsyncClient):
    query_class = ClickHouseQuery
    executor_class = AsynchExecutor
    schema_generator = AsynchSchemaGenerator
    capabilities = Capabilities("clickhouse", supports_transactions=False)
    connection_class = asynch.connection.Connection
    loop = None

    def __init__(
        self, user: str, password: str, database: str, host: str, port: SupportsInt, **kwargs: Any
    ):
        super().__init__(**kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)  # make sure port is int type
        self.extra = kwargs.copy()
        self.schema = self.extra.pop("schema", None)
        self.extra.pop("connection_name", None)
        self.extra.pop("fetch_inserted", None)
        self.loop = self.extra.pop("loop", None)
        self.connection_class = self.extra.pop("connection_class", self.connection_class)
        self.pool_minsize = int(self.extra.pop("minsize", 1))
        self.pool_maxsize = int(self.extra.pop("maxsize", 5))

        self._template: dict = {}
        self._pool: Optional[asynch.pool] = None
        self._connection = None

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "database": self.database if with_db else "",
            "minsize": self.pool_minsize,
            "maxsize": self.pool_maxsize,
            "connection_class": self.connection_class,
            "loop": self.loop,
            **self.extra,
        }
        try:
            self._pool = await asynch.create_pool(password=self.password, **self._template)
            self.log.debug("Created connection pool %s with params: %s", self._pool, self._template)
        except errors.ServerException:
            raise DBConnectionError(f"Can't connect to ClickHouse server: {self._template}")

    async def _close(self) -> None:
        if self._pool:  # pragma: nobranch
            self._pool.close()
            await self._pool.wait_closed()
            self.log.debug("Closed connection %s with params: %s", self._connection, self._template)
            self._pool = None

    async def close(self) -> None:
        await self._close()
        self._template.clear()

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f"CREATE DATABASE {self.database}")
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        try:
            await self.execute_script(f"DROP DATABASE {self.database}")
        except errors.DatabaseError:  # pragma: nocoverage
            pass
        await self.close()

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return PoolConnectionWrapper(self._pool)

    def _in_transaction(self) -> "TransactionContext":
        raise NotSupportError("ClickHouse not support transaction")

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> Any:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                print(query)
                return await cursor.execute(query, values)

    @translate_exceptions
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> Tuple[int, Sequence[dict]]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            if values:
                params = [query, *values]
            else:
                params = [query]
            if query.startswith("UPDATE") or query.startswith("DELETE"):
                res = await connection.execute(*params)
                try:
                    rows_affected = int(res.split(" ")[1])
                except Exception:  # pragma: nocoverage
                    rows_affected = 0
                return rows_affected, []

            rows = await connection.fetch(*params)
            return len(rows), rows

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:
                for sub_query in query.split(";"):
                    if sub_query:
                        await cursor.execute(sub_query)

    @translate_exceptions
    async def execute_many(self, query: str, values: List[list]) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Consider using copy_records_to_table instead
            await connection.executemany(query, values)

    @translate_exceptions
    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            if values:
                return list(map(dict, await connection.fetch(query, *values)))
            return list(map(dict, await connection.fetch(query)))
