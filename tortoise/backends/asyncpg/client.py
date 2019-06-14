import asyncio
import logging
from functools import wraps
from typing import List, Optional, SupportsInt, Union, TYPE_CHECKING  # noqa

import asyncpg
from pypika import PostgreSQLQuery

from tortoise.backends.asyncpg.executor import AsyncpgExecutor
from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    BaseTransactionWrapper,
    Capabilities,
    ConnectionWrapper,
)
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
            asyncpg.PostgresConnectionError,
            asyncpg.ConnectionDoesNotExistError,
            asyncpg.ConnectionFailureError,
            asyncpg.InterfaceError,
        ):
            # Here we assume that a connection error has happened
            # Re-create connection and re-try the function call once only.
            if getattr(self, "transaction", None):
                self._finalized = True
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
        except asyncpg.SyntaxOrAccessError as exc:
            raise OperationalError(exc)
        except asyncpg.IntegrityConstraintViolationError as exc:
            raise IntegrityError(exc)

    return translate_exceptions_


class PoolConnectionDispatcher:
    __slots__ = ("pool", "connection")
    log = logging.getLogger("db_client")

    def __init__(self, pool: asyncpg.pool.Pool) -> None:
        self.pool = pool
        self.connection = None

    async def __aenter__(self):
        self.connection = await self.pool.acquire()
        self.log.debug("Acquired connection %s", self.connection)
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.log.debug("Released connection %s", self.connection)
        await self.pool.release(self.connection)


class AsyncpgDBClient(BaseDBAsyncClient):
    DSN_TEMPLATE = "postgres://{user}:{password}@{host}:{port}/{database}"
    query_class = PostgreSQLQuery
    executor_class = AsyncpgExecutor
    schema_generator = AsyncpgSchemaGenerator
    capabilities = Capabilities("postgres", pooling=True)

    def __init__(
        self,
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
        self.extra = kwargs.copy()
        self.extra.pop("connection_name", None)
        self.extra.pop("fetch_inserted", None)
        self.extra.pop("loop", None)
        self.extra.pop("connection_class", None)
        self._pool = None  # type: Optional[asyncpg.pool.Pool]
        self.min_size = int(min_size)
        self.max_size = int(max_size)

        self._template = {}  # type: dict

        self._transaction_class = type(
            "TransactionWrapper", (TransactionWrapper, self.__class__), {}
        )

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "database": self.database if with_db else None,
            "min_size": self.min_size,
            "max_size": self.max_size,
            **self.extra,
        }
        try:
            self._pool = await asyncpg.create_pool(None, password=self.password, **self._template)
            self.log.debug("Created pool %s with params: %s", self._pool, self._template)
        except asyncpg.InvalidCatalogNameError:
            raise DBConnectionError(
                "Can't establish connection to database {}".format(self.database)
            )

    async def _close(self) -> None:
        if self._pool:  # pragma: nobranch
            try:
                await asyncio.wait_for(self._pool.close(), 10)
            except asyncio.TimeoutError:
                await self._pool.terminate()
            self.log.debug("Closed pool %s with params: %s", self._pool, self._template)
            self._template.clear()

    async def close(self) -> None:
        await self._close()
        self._pool = None

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(
            'CREATE DATABASE "{}" OWNER "{}"'.format(self.database, self.user)
        )
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        try:
            await self.execute_script('DROP DATABASE "{}"'.format(self.database))
        except asyncpg.InvalidCatalogNameError:  # pragma: nocoverage
            pass
        await self.close()

    def acquire_connection(self) -> "AsyncContextManager":
        return PoolConnectionDispatcher(self._pool)

    def _in_transaction(self) -> "TransactionWrapper":
        return self._transaction_class(None, self)

    @translate_exceptions
    @retry_connection
    async def execute_insert(self, query: str, values: list) -> Optional[asyncpg.Record]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Cache prepared statement
            stmt = await connection.prepare(query)
            return await stmt.fetchrow(*values)

    @translate_exceptions
    @retry_connection
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Consider using copy_records_to_table instead
            await connection.executemany(query, values)

    @translate_exceptions
    @retry_connection
    async def execute_query(self, query: str) -> List[dict]:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            return await connection.fetch(query)

    @translate_exceptions
    @retry_connection
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            await connection.execute(query)


class TransactionWrapper(BaseTransactionWrapper, AsyncpgDBClient):
    def __init__(
        self, connection: asyncpg.Connection, parent: Union[AsyncpgDBClient, "TransactionWrapper"]
    ) -> None:
        self._pool = parent._pool  # type: asyncpg.pool.Pool
        self._current_transaction = parent._current_transaction
        self.log = logging.getLogger("db_client")
        self._transaction_class = self.__class__
        self._old_context_value = None  # type: Optional[BaseDBAsyncClient]
        self.connection_name = parent.connection_name
        self.transaction = None
        self._finalized = False
        self._parent = parent
        self._connection = connection
        if isinstance(parent, TransactionWrapper):
            self._lock = parent._lock  # type: asyncio.Lock
        else:
            self._lock = asyncio.Lock()

    async def create_connection(self, with_db: bool) -> None:
        await self._parent.create_connection(with_db)
        self._pool = self._parent._pool

    async def _close(self) -> None:
        await self._parent._close()
        self._pool = self._parent._pool

    def acquire_connection(self) -> "AsyncContextManager":
        return ConnectionWrapper(self._connection, self._lock)

    def _in_transaction(self) -> "TransactionWrapper":
        return self._transaction_class(self._connection, self)

    @retry_connection
    async def start(self):
        if not self._connection:
            self._connection = await self._pool.acquire()
        self.transaction = self._connection.transaction()
        await self.transaction.start()
        self._old_context_value = self._current_transaction.get()
        self._current_transaction.set(self)

    async def finalize(self) -> None:
        if not self._old_context_value:
            raise OperationalError("Finalize was called before transaction start")
        self._finalized = True
        self._current_transaction.set(self._old_context_value)
        await self._pool.release(self._connection)
        self._connection = None

    async def commit(self):
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self.transaction.commit()
        await self.finalize()

    async def rollback(self):
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self.transaction.rollback()
        await self.finalize()
