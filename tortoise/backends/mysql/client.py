import asyncio
import logging
from functools import wraps
from typing import List, Optional, SupportsInt, Union, TYPE_CHECKING  # noqa

import aiomysql
import pymysql
from pypika import MySQLQuery

from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    BaseTransactionWrapper,
    Capabilities,
    ConnectionWrapper,
)
from tortoise.backends.mysql.executor import MySQLExecutor
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.exceptions import (
    DBConnectionError,
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

if TYPE_CHECKING:
    from typing import AsyncContextManager


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
                await self._close()
                await self.create_connection(with_db=True)
                logging.info("Reconnected")
            except Exception as e:
                logging.info("Failed to reconnect: %s", str(e))
                raise

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
            raise OperationalError(exc) from exc
        except pymysql.err.IntegrityError as exc:
            raise IntegrityError(exc) from exc

    return translate_exceptions_


class PoolConnectionDispatcher:
    __slots__ = ("pool", "connection")
    log = logging.getLogger("db_client")

    def __init__(self, pool: aiomysql.pool.Pool) -> None:
        self.pool = pool
        self.connection = None  # type: aiomysql.Connection

    async def __aenter__(self):
        self.connection = await self.pool.acquire()
        self.log.debug("Acquired connection %s", self.connection)
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.connection.rollback()
        else:
            await self.connection.commit()
        self.pool.release(self.connection)
        self.log.debug("Released connection %s", self.connection)


class MySQLClient(BaseDBAsyncClient):
    query_class = MySQLQuery
    executor_class = MySQLExecutor
    schema_generator = MySQLSchemaGenerator
    capabilities = Capabilities(
        "mysql", safe_indexes=False, requires_limit=True, inline_comment=True, pooling=True
    )

    def __init__(
        self,
        *,
        user: str,
        password: str,
        database: str,
        host: str,
        port: SupportsInt,
        min_size: SupportsInt = 10,
        max_size: SupportsInt = 10,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)  # make sure port is int type
        self.min_size = int(min_size)
        self.max_size = int(max_size)
        self.extra = kwargs.copy()
        self.extra.pop("connection_name", None)
        self.extra.pop("fetch_inserted", None)
        self.extra.pop("db", None)
        self.extra.pop("autocommit", None)

        self._template = {}  # type: dict
        self._pool = None  # type: Optional[aiomysql.pool.Pool]

        self._transaction_class = type(
            "TransactionWrapper", (TransactionWrapper, self.__class__), {}
        )

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "db": self.database if with_db else None,
            "autocommit": False,
            "minsize": self.min_size,
            "maxsize": self.max_size,
            **self.extra,
        }
        try:
            self._pool = await aiomysql.create_pool(password=self.password, **self._template)
            self.log.debug("Created connection %s with params: %s", self._pool, self._template)
        except pymysql.err.OperationalError as e:
            raise DBConnectionError(
                "Can't connect to MySQL server: {template}".format(template=self._template)
            ) from e

    async def _close(self) -> None:
        if self._pool:  # pragma: nobranch
            self._pool.close()
            self.log.debug("Closed connection %s with params: %s", self._pool, self._template)
            self._template.clear()

    async def close(self) -> None:
        await self._close()
        self._pool = None

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script("CREATE DATABASE {}".format(self.database))
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        try:
            await self.execute_script("DROP DATABASE {}".format(self.database))
        except pymysql.err.DatabaseError:  # pragma: nocoverage
            pass
        await self.close()

    def acquire_connection(self) -> "AsyncContextManager":
        return PoolConnectionDispatcher(self._pool)

    def _in_transaction(self):
        return self._transaction_class(None, self)

    async def _release(self, connection: aiomysql.Connection):
        if not self._pool:
            raise OperationalError("Can't release connection if pool is not initialized")
        self._pool.release(connection)

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
    async def execute_query(self, query: str) -> List[aiomysql.DictCursor]:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query)
                return await cursor.fetchall()

    @translate_exceptions
    @retry_connection
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:
                await cursor.execute(query)


class TransactionWrapper(BaseTransactionWrapper, MySQLClient):
    def __init__(
        self,
        connection: Optional[aiomysql.Connection],
        parent: Union[MySQLClient, "TransactionWrapper"],
    ):
        self.connection_name = parent.connection_name
        self._current_transaction = parent._current_transaction
        self.log = logging.getLogger("db_client")
        self._transaction_class = self.__class__
        self._finalized = None  # type: Optional[bool]
        self._old_context_value = None  # type: Optional[BaseDBAsyncClient]
        self.fetch_inserted = parent.fetch_inserted
        self._parent = parent
        self._connection = connection
        self._pool = parent._pool
        if isinstance(parent, TransactionWrapper):
            self._lock = parent._lock  # type: asyncio.Lock
        else:
            self._lock = asyncio.Lock()

    async def create_connection(self, with_db: bool) -> None:
        await self._parent.create_connection(with_db)
        self._pool = self._parent._pool

    async def _close(self) -> None:
        await self._parent._release(self._connection)

    def acquire_connection(self) -> "AsyncContextManager":
        return ConnectionWrapper(self._connection, self._lock)

    def _in_transaction(self):
        return self._transaction_class(self._connection, self)

    @retry_connection
    async def start(self):
        if not self._connection:
            self._connection = await self._pool.acquire()
        await self._connection.begin()
        self._finalized = False
        self._old_context_value = self._current_transaction.get()
        self._current_transaction.set(self)

    async def finalize(self) -> None:
        if not self._old_context_value:
            raise OperationalError("Finalize was called before transaction start")
        self._finalized = True
        self._current_transaction.set(self._old_context_value)
        await self._parent._release(self._connection)

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if not self._connection:
            raise OperationalError("Can't commit transaction without starting it")
        await self._connection.commit()
        await self.finalize()

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if not self._connection:
            raise OperationalError("Can't rollback transaction without starting it")
        await self._connection.rollback()
        await self.finalize()
