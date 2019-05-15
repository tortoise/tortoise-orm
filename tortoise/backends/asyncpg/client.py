import asyncio
import logging
from functools import wraps
from typing import List, Optional, SupportsInt  # noqa

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


def translate_exceptions(func):
    @wraps(func)
    async def wrapped(self, query, *args):
        try:
            return await func(self, query, *args)
        except asyncpg.exceptions.SyntaxOrAccessError as exc:
            raise OperationalError(exc)
        except asyncpg.exceptions.IntegrityConstraintViolationError as exc:
            raise IntegrityError(exc)

    return wrapped


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

    async def close(self) -> None:
        if self._connection:  # pragma: nobranch
            await self._connection.close()
            self.log.debug("Closed connection %s with params: %s", self._connection, self._template)
            self._template.clear()
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
        return self._transaction_class(self.connection_name, self._connection, self._lock)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Cache prepared statement
            stmt = await connection.prepare(query)
            return await stmt.fetchval(*values)

    @translate_exceptions
    async def execute_query(self, query: str) -> List[dict]:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            return await connection.fetch(query)

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            await connection.execute(query)


class TransactionWrapper(AsyncpgDBClient, BaseTransactionWrapper):
    def __init__(self, connection_name: str, connection, lock) -> None:
        self._connection = connection
        self._lock = lock
        self.log = logging.getLogger("db_client")
        self._transaction_class = self.__class__
        self._old_context_value = None
        self.connection_name = connection_name
        self.transaction = None

    async def start(self):
        self.transaction = self._connection.transaction()
        await self.transaction.start()
        current_transaction = current_transaction_map[self.connection_name]
        self._old_context_value = current_transaction.get()
        current_transaction.set(self)

    async def commit(self):
        try:
            await self.transaction.commit()
        except asyncpg.exceptions._base.InterfaceError as exc:
            raise TransactionManagementError(exc)
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def rollback(self):
        try:
            await self.transaction.rollback()
        except asyncpg.exceptions._base.InterfaceError as exc:
            raise TransactionManagementError(exc)
        current_transaction_map[self.connection_name].set(self._old_context_value)
