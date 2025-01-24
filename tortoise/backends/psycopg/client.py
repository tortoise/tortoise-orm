from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import _AsyncGeneratorContextManager
from ssl import SSLContext
from typing import Any, TypeVar, cast

import psycopg
import psycopg.conninfo
import psycopg.pq
import psycopg.rows
import psycopg_pool
from pypika_tortoise import SqlContext
from pypika_tortoise.dialects.postgresql import PostgreSQLQuery, PostgreSQLQueryBuilder
from pypika_tortoise.terms import Parameterizer

import tortoise.backends.base.client as base_client
import tortoise.backends.base_postgres.client as postgres_client
import tortoise.backends.psycopg.executor as executor
import tortoise.exceptions as exceptions
from tortoise.backends.psycopg.schema_generator import PsycopgSchemaGenerator

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


class AsyncConnectionPool(psycopg_pool.AsyncConnectionPool):
    # TortoiseORM has this interface hardcoded in the tests so we need to support it
    async def acquire(self, *args, **kwargs) -> psycopg.AsyncConnection:
        return await self.getconn(*args, **kwargs)

    async def release(self, connection: psycopg.AsyncConnection):
        await self.putconn(connection)


class PsycopgSQLQuery(PostgreSQLQuery):
    @classmethod
    def _builder(cls, **kwargs) -> "PostgreSQLQueryBuilder":
        return PsycopgSQLQueryBuilder(**kwargs)


class PsycopgSQLQueryBuilder(PostgreSQLQueryBuilder):
    """
    Psycopg opted to use a custom parameter placeholder, so we need to override the default
    """

    def get_parameterized_sql(self, ctx: SqlContext | None = None) -> tuple[str, list]:
        if not ctx:
            ctx = self.QUERY_CLS.SQL_CONTEXT
        if not ctx.parameterizer:
            ctx = ctx.copy(parameterizer=Parameterizer(placeholder_factory=lambda _: "%s"))
        return super().get_parameterized_sql(ctx)


class PsycopgClient(postgres_client.BasePostgresClient):
    query_class: type[PsycopgSQLQuery] = PsycopgSQLQuery
    executor_class: type[executor.PsycopgExecutor] = executor.PsycopgExecutor
    schema_generator: type[PsycopgSchemaGenerator] = PsycopgSchemaGenerator
    _pool: AsyncConnectionPool | None = None
    _connection: psycopg.AsyncConnection
    default_timeout: float = 30

    @postgres_client.translate_exceptions
    async def create_connection(self, with_db: bool) -> None:
        if self._pool is not None:
            raise RuntimeError("Connection pool already created")

        self.server_settings["options"] = f"-c search_path={self.schema}" if self.schema else None
        self.server_settings["application_name"] = self.application_name

        extra = self.extra.copy()
        extra.setdefault("timeout", self.default_timeout)
        ssl: SSLContext = extra.pop("ssl", None)
        if ssl:
            if isinstance(ssl, SSLContext) and ssl.check_hostname:
                self.server_settings["sslmode"] = "verify-full"
            else:
                self.server_settings["sslmode"] = "require"

        conninfo = psycopg.conninfo.make_conninfo(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.database if with_db else None,
            **self.server_settings,
        )

        self._template = {
            "conninfo": conninfo,
            "min_size": self.pool_minsize,
            "max_size": self.pool_maxsize,
            "kwargs": {
                "autocommit": True,
                "row_factory": psycopg.rows.dict_row,
            },
            "connection_class": psycopg.AsyncConnection,
            **extra,
        }

        try:
            self._pool = await self.create_pool(**self._template)
            # Immediately test the connection because the test suite expects it to check if the
            # connection is valid.
            await self._pool.open(wait=True, timeout=extra["timeout"])
            self.log.debug("Created connection pool %s with params: %s", self._pool, self._template)
        except (psycopg.errors.InvalidCatalogName, psycopg_pool.PoolTimeout):
            raise exceptions.DBConnectionError(
                f"Can't establish connection to database {self.database}"
            )

    async def create_pool(self, **kwargs) -> AsyncConnectionPool:
        pool = AsyncConnectionPool(open=False, **kwargs)
        await pool.open()
        return pool

    async def db_delete(self) -> None:
        try:
            return await super().db_delete()
        except psycopg.errors.InvalidCatalogName:  # pragma: nocoverage
            pass

    async def execute_insert(self, query: str, values: list) -> Any | None:
        inserted, rows = await self.execute_query(query, values)
        if rows:
            return rows[0]
        else:
            return None

    @postgres_client.translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        connection: psycopg.AsyncConnection
        async with self.acquire_connection() as connection:
            async with connection.cursor() as cursor:
                self.log.debug("%s: %s", query, values)
                await cursor.executemany(query, values)

    @postgres_client.translate_exceptions
    async def execute_query(
        self,
        query: str,
        values: list | None = None,
        row_factory=psycopg.rows.dict_row,
    ) -> tuple[int, list[dict]]:
        connection: psycopg.AsyncConnection
        async with self.acquire_connection() as connection:
            cursor: psycopg.AsyncCursor | psycopg.AsyncServerCursor
            async with connection.cursor(row_factory=row_factory) as cursor:
                self.log.debug("%s: %s", query, values)
                await cursor.execute(query, values)

                rowcount = int(cursor.rowcount or cursor.rownumber or 0)

                if cursor.pgresult and cursor.pgresult.status == psycopg.pq.ExecStatus.TUPLES_OK:
                    rows = await cursor.fetchall()
                else:
                    rows = []

                return rowcount, cast(list[dict], rows)

    async def execute_query_dict(self, query: str, values: list | None = None) -> list[dict]:
        rowcount, rows = await self.execute_query(query, values, row_factory=psycopg.rows.dict_row)
        return rows

    async def _expire_connections(self) -> None:
        if self._pool:  # pragma: nobranch
            await self._pool.close()
            self._pool = await self.create_pool(**self._template)

    async def _close(self) -> None:
        if self._pool:  # pragma: nobranch
            pool = self._pool
            self._pool = None
            await pool.close(10)
            self.log.debug("Closed connection pool %s with params: %s", self._pool, self._template)

    async def _translate_exceptions(self, func, *args, **kwargs) -> Exception:
        try:
            return await func(self, *args, **kwargs)
        except (
            psycopg.errors.SyntaxErrorOrAccessRuleViolation,
            psycopg.errors.DataException,
            psycopg.errors.UndefinedTable,
        ) as exc:
            raise exceptions.OperationalError(exc)
        except psycopg.errors.IntegrityError as exc:
            raise exceptions.IntegrityError(exc)
        except (
            psycopg.errors.InvalidTransactionState,
            psycopg.errors.InFailedSqlTransaction,
        ) as exc:
            raise exceptions.TransactionManagementError(exc)

    def _in_transaction(self) -> base_client.TransactionContext:
        return base_client.TransactionContextPooled(TransactionWrapper(self), self._pool_init_lock)


class TransactionWrapper(PsycopgClient, base_client.TransactionalDBClient):
    """A transactional connection wrapper for psycopg.

    psycopg implements nested transactions (savepoints) natively, so we don't need to.
    """

    _connection: psycopg.AsyncConnection

    def __init__(self, connection: PsycopgClient) -> None:
        self._connection: psycopg.AsyncConnection = connection._connection
        self._lock = asyncio.Lock()
        self.log = connection.log
        self.connection_name = connection.connection_name
        self._transaction: _AsyncGeneratorContextManager[psycopg.AsyncTransaction] | None = None
        self._finalized = False
        self._parent = connection

    def _in_transaction(self) -> base_client.TransactionContext:
        # since we need to store the transaction object for each transaction block,
        # we need to wrap the connection with its own TransactionWrapper
        return base_client.NestedTransactionContext(TransactionWrapper(self))

    def acquire_connection(self) -> base_client.ConnectionWrapper[psycopg.AsyncConnection]:
        return base_client.ConnectionWrapper(self._lock, self)

    @postgres_client.translate_exceptions
    async def begin(self) -> None:
        self._transaction = self._connection.transaction()
        await self._transaction.__aenter__()

    async def savepoint(self) -> None:
        return await self.begin()

    async def commit(self) -> None:
        if not self._transaction:
            raise exceptions.TransactionManagementError("Transaction is in invalid state")
        if self._finalized:
            raise exceptions.TransactionManagementError("Transaction already finalised")

        await self._transaction.__aexit__(None, None, None)
        self._finalized = True

    async def release_savepoint(self) -> None:
        await self.commit()

    async def rollback(self) -> None:
        if not self._transaction:
            raise exceptions.TransactionManagementError("Transaction is in invalid state")
        if self._finalized:
            raise exceptions.TransactionManagementError("Transaction already finalised")

        await self._transaction.__aexit__(psycopg.Rollback, psycopg.Rollback(), None)
        self._finalized = True

    async def savepoint_rollback(self) -> None:
        await self.rollback()
