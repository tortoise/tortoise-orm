import asyncio
import logging
from functools import wraps
from typing import Any, List, Optional, SupportsInt  # noqa

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
from tortoise.transactions import current_transaction_map


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
            await self._lock.acquire()
            logging.info("Attempting reconnect")
            try:
                await self._close()
                await self.create_connection(with_db=True)
                logging.info("Reconnected")
            except Exception as e:
                logging.info("Failed to reconnect: %s", str(e))
                raise
            finally:
                self._lock.release()

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


class AsyncpgDBClient(BaseDBAsyncClient):
    DSN_TEMPLATE = "postgres://{user}:{password}@{host}:{port}/{database}"
    query_class = PostgreSQLQuery
    executor_class = AsyncpgExecutor
    schema_generator = AsyncpgSchemaGenerator
    capabilities = Capabilities("postgres")

    def __init__(
        self, user: str, password: str, database: str, host: str, port: SupportsInt, **kwargs
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

        self._template = {}  # type: dict
        self._connection = None  # Type: Optional[asyncpg.Connection]
        self._lock = asyncio.Lock()

        self._transaction_class = type(
            "TransactionWrapper", (TransactionWrapper, self.__class__), {}
        )

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "database": self.database if with_db else None,
            **self.extra,
        }
        try:
            self._connection = await asyncpg.connect(None, password=self.password, **self._template)
            self.log.debug(
                "Created connection %s with params: %s", self._connection, self._template
            )
        except asyncpg.InvalidCatalogNameError:
            raise DBConnectionError(
                "Can't establish connection to database {}".format(self.database)
            )

    async def _close(self) -> None:
        if self._connection:  # pragma: nobranch
            await self._connection.close()
            self.log.debug("Closed connection %s with params: %s", self._connection, self._template)
            self._template.clear()

    async def close(self) -> None:
        await self._close()
        self._connection = None

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

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._connection, self._lock)

    def _in_transaction(self) -> "TransactionWrapper":
        return self._transaction_class(self)

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


class TransactionWrapper(AsyncpgDBClient, BaseTransactionWrapper):
    def __init__(self, connection) -> None:
        self._connection = connection._connection
        self._lock = connection._lock
        self.log = logging.getLogger("db_client")
        self._transaction_class = self.__class__
        self._old_context_value = None
        self.connection_name = connection.connection_name
        self.transaction = None
        self._finalized = False
        self._parent = connection

    async def create_connection(self, with_db: bool) -> None:
        await self._parent.create_connection(with_db)
        self._connection = self._parent._connection

    async def _close(self) -> None:
        await self._parent._close()
        self._connection = self._parent._connection

    @retry_connection
    async def start(self):
        self.transaction = self._connection.transaction()
        await self.transaction.start()
        current_transaction = current_transaction_map[self.connection_name]
        self._old_context_value = current_transaction.get()
        current_transaction.set(self)

    def release(self) -> None:
        self._finalized = True
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def commit(self):
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self.transaction.commit()
        self.release()

    async def rollback(self):
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self.transaction.rollback()
        self.release()
