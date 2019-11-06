import asyncio
import logging
from functools import wraps
from typing import List, Optional, SupportsInt, Union

import aiomysql
import pymysql
from pypika import MySQLQuery

from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    BaseTransactionWrapper,
    Capabilities,
    ConnectionWrapper,
    NestedTransactionContext,
    PoolConnectionWrapper,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.backends.mysql.executor import MySQLExecutor
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.exceptions import (
    DBConnectionError,
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)


def retry_connection(func):
    @wraps(func)
    async def retry_connection_(self, *args):
        try:
            return await func(self, *args)
        except (
            RuntimeError,
            pymysql.err.OperationalError,
            pymysql.err.InternalError,
            pymysql.err.InterfaceError,
        ):
            # Here we assume that a connection error has happened
            # Re-create connection and re-try the function call once only.
            if getattr(self, "_finalized", None) is False:
                raise TransactionManagementError("Connection gone away during transaction")
            logging.info("Attempting reconnect")
            try:
                async with self.acquire_connection() as connection:
                    await connection.ping()
                    logging.info("Reconnected")
            except Exception as e:
                raise DBConnectionError("Failed to reconnect: %s", str(e))

            return await func(self, *args)

    return retry_connection_


def translate_exceptions(func):
    @wraps(func)
    async def translate_exceptions_(self, *args):
        try:
            return await func(self, *args)
        except (
            pymysql.err.OperationalError,
            pymysql.err.ProgrammingError,
            pymysql.err.DataError,
            pymysql.err.InternalError,
            pymysql.err.NotSupportedError,
        ) as exc:
            raise OperationalError(exc)
        except pymysql.err.IntegrityError as exc:
            raise IntegrityError(exc)

    return translate_exceptions_


class MySQLClient(BaseDBAsyncClient):
    query_class = MySQLQuery
    executor_class = MySQLExecutor
    schema_generator = MySQLSchemaGenerator
    capabilities = Capabilities("mysql", requires_limit=True, inline_comment=True)

    def __init__(
        self, *, user: str, password: str, database: str, host: str, port: SupportsInt, **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)  # make sure port is int type
        self.extra = kwargs.copy()
        self.storage_engine = self.extra.pop("storage_engine", "")
        self.extra.pop("connection_name", None)
        self.extra.pop("fetch_inserted", None)
        self.extra.pop("db", None)
        self.extra.pop("autocommit", None)
        self.charset = self.extra.pop("charset", "")
        self.pool_minsize = int(self.extra.pop("minsize", 1))
        self.pool_maxsize = int(self.extra.pop("maxsize", 5))

        self._template: dict = {}
        self._pool: Optional[aiomysql.Pool] = None
        self._connection = None

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "db": self.database if with_db else None,
            "autocommit": True,
            "charset": self.charset,
            "minsize": self.pool_minsize,
            "maxsize": self.pool_maxsize,
            **self.extra,
        }
        try:
            self._pool = await aiomysql.create_pool(password=self.password, **self._template)

            if isinstance(self._pool, aiomysql.Pool):
                async with self.acquire_connection() as connection:
                    async with connection.cursor() as cursor:
                        if self.storage_engine:
                            await cursor.execute(
                                f"SET default_storage_engine='{self.storage_engine}';"
                            )
                            if self.storage_engine.lower() != "innodb":
                                self.capabilities.__dict__["supports_transactions"] = False

            self.log.debug("Created connection %s pool with params: %s", self._pool, self._template)
        except pymysql.err.OperationalError:
            raise DBConnectionError(f"Can't connect to MySQL server: {self._template}")

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
        except pymysql.err.DatabaseError:  # pragma: nocoverage
            pass
        await self.close()

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return PoolConnectionWrapper(self._pool)

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self))

    @translate_exceptions
    @retry_connection
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.execute(query, values)
                return cursor.lastrowid  # return auto-generated id

    @translate_exceptions
    @retry_connection
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.executemany(query, values)

    @translate_exceptions
    @retry_connection
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> List[aiomysql.DictCursor]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, values)
                return await cursor.fetchall()

    @translate_exceptions
    @retry_connection
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:
                await cursor.execute(query)


class TransactionWrapper(MySQLClient, BaseTransactionWrapper):
    def __init__(self, connection) -> None:
        self.connection_name = connection.connection_name
        self._connection: aiomysql.Connection = connection._connection
        self._lock = asyncio.Lock()
        self.log = connection.log
        self._finalized: Optional[bool] = None
        self.fetch_inserted = connection.fetch_inserted
        self._parent = connection

    def _in_transaction(self) -> "TransactionContext":
        return NestedTransactionContext(self)

    async def create_connection(self, with_db: bool) -> None:
        await self._parent.create_connection(with_db)

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._connection, self._lock)

    @retry_connection
    async def start(self) -> None:
        await self._connection.begin()
        self._finalized = False

    async def commit(self, finalize: bool = True) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        if finalize:
            self._finalized = True

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        self._finalized = True
