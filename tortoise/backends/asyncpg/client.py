import asyncio
from typing import Any, Callable, List, Optional, Tuple, TypeVar

import asyncpg
from asyncpg.transaction import Transaction

from tortoise.backends.asyncpg.executor import AsyncpgExecutor
from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
from tortoise.backends.base.client import (
    TransactionalDBClient,
    ConnectionWrapper,
    NestedTransactionContext,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.backends.base_postgres.client import (
    BasePostgresClient,
    translate_exceptions,
)
from tortoise.exceptions import (
    DBConnectionError,
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


class AsyncpgDBClient(BasePostgresClient):
    executor_class = AsyncpgExecutor
    schema_generator = AsyncpgSchemaGenerator
    connection_class = asyncpg.connection.Connection
    _pool: Optional[asyncpg.Pool]
    _connection: Optional[asyncpg.connection.Connection] = None

    async def create_connection(self, with_db: bool) -> None:
        if self.schema:
            self.server_settings["search_path"] = self.schema

        if self.application_name:
            self.server_settings["application_name"] = self.application_name

        self._template = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "database": self.database if with_db else None,
            "min_size": self.pool_minsize,
            "max_size": self.pool_maxsize,
            "connection_class": self.connection_class,
            "loop": self.loop,
            "server_settings": self.server_settings,
            **self.extra,
        }
        try:
            self._pool = await self.create_pool(password=self.password, **self._template)
            self.log.debug("Created connection pool %s with params: %s", self._pool, self._template)
        except asyncpg.InvalidCatalogNameError as ex:
            msg = "Can't establish connection to "
            if with_db:
                msg += f"database {self.database}"
            else:
                msg += f"default database. Verify environment PGDATABASE. Exception: {ex}"
            raise DBConnectionError(msg)

    async def create_pool(self, **kwargs) -> asyncpg.Pool:
        return await asyncpg.create_pool(None, **kwargs)

    async def _expire_connections(self) -> None:
        if self._pool:  # pragma: nobranch
            await self._pool.expire_connections()

    async def _close(self) -> None:
        if self._pool:  # pragma: nobranch
            try:
                await asyncio.wait_for(self._pool.close(), 10)
            except asyncio.TimeoutError:  # pragma: nocoverage
                self._pool.terminate()
            self._pool = None
            self.log.debug("Closed connection pool %s with params: %s", self._pool, self._template)

    async def _translate_exceptions(self, func, *args, **kwargs) -> Exception:
        try:
            return await func(self, *args, **kwargs)
        except (asyncpg.SyntaxOrAccessError, asyncpg.exceptions.DataError) as exc:
            raise OperationalError(exc)
        except asyncpg.IntegrityConstraintViolationError as exc:
            raise IntegrityError(exc)
        except asyncpg.InvalidTransactionStateError as exc:  # pragma: nocoverage
            raise TransactionManagementError(exc)

    async def db_delete(self) -> None:
        try:
            return await super().db_delete()
        except asyncpg.InvalidCatalogNameError:  # pragma: nocoverage
            pass
        await self.close()

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self), self._pool_init_lock)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> Optional[asyncpg.Record]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Cache prepared statement
            return await connection.fetchrow(query, *values)

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Consider using copy_records_to_table instead
            transaction = connection.transaction()
            await transaction.start()
            try:
                await connection.executemany(query, values)
            except Exception:
                await transaction.rollback()
                raise
            else:
                await transaction.commit()

    @translate_exceptions
    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> Tuple[int, List[dict]]:
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
    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            if values:
                return list(map(dict, await connection.fetch(query, *values)))
            return list(map(dict, await connection.fetch(query)))


class TransactionWrapper(AsyncpgDBClient, TransactionalDBClient):
    """A transactional connection wrapper for psycopg.

    asyncpg implements nested transactions (savepoints) natively, so we don't need to.
    """

    def __init__(self, connection: AsyncpgDBClient) -> None:
        self._connection: asyncpg.Connection = connection._connection
        self._lock = asyncio.Lock()
        self.log = connection.log
        self.connection_name = connection.connection_name
        self.transaction: Optional[Transaction] = None
        self._finalized = False
        self._parent: AsyncpgDBClient = connection

    def _in_transaction(self) -> "TransactionContext":
        # since we need to store the transaction object for each transaction block,
        # we need to wrap the connection with its own TransactionWrapper
        return NestedTransactionContext(TransactionWrapper(self))

    def acquire_connection(self) -> ConnectionWrapper[asyncpg.Connection]:
        return ConnectionWrapper(self._lock, self)

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Consider using copy_records_to_table instead
            await connection.executemany(query, values)

    @translate_exceptions
    async def begin(self) -> None:
        self.transaction = self._connection.transaction()
        await self.transaction.start()

    async def savepoint(self) -> None:
        return await self.begin()

    async def commit(self) -> None:
        if not self.transaction:
            raise TransactionManagementError("Transaction is in invalid state")
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self.transaction.commit()
        self._finalized = True

    async def release_savepoint(self) -> None:
        return await self.commit()

    async def rollback(self) -> None:
        if not self.transaction:
            raise TransactionManagementError("Transaction is in invalid state")
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self.transaction.rollback()
        self._finalized = True

    async def savepoint_rollback(self) -> None:
        await self.rollback()
