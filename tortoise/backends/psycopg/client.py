import asyncio
import contextlib
from collections import namedtuple
from ssl import SSLContext
from typing import Any, Callable, List, Optional, Tuple, TypeVar

import psycopg
import psycopg_pool
from psycopg import errors
from psycopg.conninfo import make_conninfo
from psycopg.pq import ExecStatus
from psycopg.rows import dict_row

from tortoise.backends.base.client import (
    BaseTransactionWrapper,
    ConnectionWrapper,
    NestedTransactionPooledContext,
    PoolConnectionWrapper,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.backends.base_postgres.client import BasePostgresClient, translate_exceptions
from tortoise.backends.psycopg.executor import PsycopgExecutor
from tortoise.backends.psycopg.schema_generator import PsycopgSchemaGenerator
from tortoise.exceptions import (
    DBConnectionError,
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


class AsyncConnectionPool(psycopg_pool.AsyncConnectionPool):
    # TortoiseORM has this interface hardcoded in the tests so we need to support it
    async def acquire(self, *args, **kwargs) -> psycopg.AsyncConnection:
        return await self.getconn(*args, **kwargs)

    async def release(self, connection: psycopg.AsyncConnection):
        await self.putconn(connection)


class PsycopgClient(BasePostgresClient):
    executor_class = PsycopgExecutor
    schema_generator = PsycopgSchemaGenerator
    _pool: Optional[AsyncConnectionPool]

    @translate_exceptions
    async def create_connection(self, with_db: bool) -> None:
        assert not self._pool, "Connection already created"
        self.server_settings["options"] = f"-c search_path={self.schema}" if self.schema else None
        self.server_settings["application_name"] = self.application_name

        extra = self.extra.copy()
        extra.setdefault("timeout", 30)
        ssl: SSLContext = extra.pop("ssl", None)
        if ssl:
            if isinstance(ssl, SSLContext) and ssl.check_hostname:
                self.server_settings["sslmode"] = "verify-full"
            else:
                self.server_settings["sslmode"] = "require"

        conninfo = make_conninfo(
            **{
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "password": self.password,
                "dbname": self.database if with_db else None,
                **self.server_settings,
            }
        )

        self._template = {
            "conninfo": conninfo,
            "min_size": self.pool_minsize,
            "max_size": self.pool_maxsize,
            "kwargs": {
                "autocommit": True,
                "row_factory": dict_row,
            },
            "connection_class": psycopg.AsyncConnection,
            **extra,
        }

        try:
            self._pool = await self.create_pool(**self._template)
            # Immediately test the connection because the TortoiseORM test suite expects it to
            # check if the connection is valid.
            await self._pool.open(wait=True, timeout=extra["timeout"])

            self.log.debug("Created connection pool %s with params: %s", self._pool, self._template)
        except (errors.InvalidCatalogName, psycopg_pool.PoolTimeout) as e:
            raise DBConnectionError(f"Can't establish connection to database {self.database}")

    async def create_pool(self, **kwargs) -> AsyncConnectionPool:
        return AsyncConnectionPool(**kwargs)

    async def db_delete(self) -> None:
        try:
            return await super().db_delete()
        except psycopg.errors.InvalidCatalogName:  # pragma: nocoverage
            pass

    async def execute_insert(self, query: str, values: list) -> Optional[Any]:
        inserted, rows = await self.execute_query(query, values)
        if rows:
            return rows[0]

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            async with connection.cursor() as cursor:
                self.log.debug("%s: %s", query, values)
                try:
                    await cursor.executemany(query, values)
                except Exception:
                    await connection.rollback()
                    raise
                else:
                    await connection.commit()

    @translate_exceptions
    async def execute_query(
        self,
        query: str,
        values: Optional[list] = None,
        row_factory=dict_row,
    ) -> Tuple[int, List[namedtuple]]:
        connection: psycopg.AsyncConnection
        async with self.acquire_connection() as connection:
            cursor: psycopg.AsyncCursor | psycopg.AsyncServerCursor
            async with connection.cursor(row_factory=row_factory) as cursor:
                self.log.debug("%s: %s", query, values)
                try:
                    await cursor.execute(query, values)
                except errors.IntegrityError:
                    await connection.rollback()
                    raise

                rowcount = cursor.rowcount or cursor.rownumber

                if cursor.pgresult.status == ExecStatus.TUPLES_OK:
                    rows = await cursor.fetchall()
                else:
                    rows = []

                return rowcount, rows

    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        rowcount, rows = await self.execute_query(query, values, row_factory=dict_row)
        return rows

    async def _expire_connections(self) -> None:
        if self._pool:  # pragma: nobranch
            await self._pool.close()
            self._pool = await self.create_pool(**self._template)

    async def _close(self) -> None:
        if self._pool:  # pragma: nobranch
            pool = self._pool
            self._pool = None
            await asyncio.wait_for(pool.close(10), 10)
            self.log.debug("Closed connection pool %s with params: %s", self._pool, self._template)

    async def _translate_exceptions(self, func, *args, **kwargs) -> Exception:
        try:
            return await func(self, *args, **kwargs)
        except (
            errors.SyntaxErrorOrAccessRuleViolation,
            errors.DataException,
            errors.UndefinedTable,
        ) as exc:
            raise OperationalError(exc)
        except errors.IntegrityError as exc:
            raise IntegrityError(exc)
        except (errors.InvalidTransactionState, errors.InFailedSqlTransaction) as exc:
            raise TransactionManagementError(exc)
        except errors.UniqueViolation as exc:
            raise IntegrityError(exc)

    @contextlib.asynccontextmanager
    async def acquire_connection(self) -> psycopg.AsyncConnection:
        try:
            async with self._pool.connection() as connection:
                yield connection

        except psycopg_pool.PoolTimeout as exc:
            raise DBConnectionError(f"Can't establish connection to database {self.database}")

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self))


class TransactionWrapper(PsycopgClient, BaseTransactionWrapper):
    def __init__(self, connection: PsycopgClient) -> None:
        self._connection: psycopg.AsyncConnection = connection._connection
        self._lock = asyncio.Lock()
        self._trxlock = asyncio.Lock()
        self.log = connection.log
        self.connection_name = connection.connection_name
        self.transaction: psycopg.AsyncTransaction = None
        self._finalized = False
        self._parent = connection

    def _in_transaction(self) -> "TransactionContext":
        return NestedTransactionPooledContext(self)

    def acquire_connection(self) -> "ConnectionWrapper":
        return ConnectionWrapper(self._connection, self._lock)

    @translate_exceptions
    async def xexecute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            async with connection.cursor() as cursor:
                self.log.debug("%s: %s", query, values)
                await cursor.executemany(query, values)

    @translate_exceptions
    async def start(self) -> None:
        # We're not using explicit transactions here because psycopg takes care of that
        # automatically when autocommit is disabled.
        await self._connection.set_autocommit(False)

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")

        await self._connection.commit()
        await self._connection.set_autocommit(True)
        self.transaction = None
        self._finalized = True

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")

        # await self.transaction.__aexit__(None, None, None)
        await self._connection.rollback()
        await self._connection.set_autocommit(True)
        self.transaction = None
        # await self._connection.set_autocommit(True)
        self._finalized = True
