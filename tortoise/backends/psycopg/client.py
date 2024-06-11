import asyncio
import typing
from ssl import SSLContext

import psycopg
import psycopg.conninfo
import psycopg.pq
import psycopg.rows
import psycopg_pool

import tortoise.backends.base.client as base_client
import tortoise.backends.base_postgres.client as postgres_client
import tortoise.backends.psycopg.executor as executor
import tortoise.exceptions as exceptions
from tortoise.backends.base.client import PoolConnectionWrapper
from tortoise.backends.psycopg.schema_generator import PsycopgSchemaGenerator

FuncType = typing.Callable[..., typing.Any]
F = typing.TypeVar("F", bound=FuncType)


class AsyncConnectionPool(psycopg_pool.AsyncConnectionPool):
    # TortoiseORM has this interface hardcoded in the tests so we need to support it
    async def acquire(self, *args, **kwargs) -> psycopg.AsyncConnection:
        return await self.getconn(*args, **kwargs)

    async def release(self, connection: psycopg.AsyncConnection):
        await self.putconn(connection)


class PsycopgClient(postgres_client.BasePostgresClient):
    executor_class: typing.Type[executor.PsycopgExecutor] = executor.PsycopgExecutor
    schema_generator: typing.Type[PsycopgSchemaGenerator] = PsycopgSchemaGenerator
    _pool: typing.Optional[AsyncConnectionPool] = None
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
        return AsyncConnectionPool(**kwargs)

    async def db_delete(self) -> None:
        try:
            return await super().db_delete()
        except psycopg.errors.InvalidCatalogName:  # pragma: nocoverage
            pass

    async def execute_insert(self, query: str, values: list) -> typing.Optional[typing.Any]:
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
                try:
                    await cursor.executemany(query, values)
                except Exception:
                    await connection.rollback()
                    raise
                else:
                    await connection.commit()

    @postgres_client.translate_exceptions
    async def execute_query(
        self,
        query: str,
        values: typing.Optional[list] = None,
        row_factory=psycopg.rows.dict_row,
    ) -> typing.Tuple[int, typing.List[dict]]:
        connection: psycopg.AsyncConnection
        async with self.acquire_connection() as connection:
            cursor: typing.Union[psycopg.AsyncCursor, psycopg.AsyncServerCursor]
            async with connection.cursor(row_factory=row_factory) as cursor:
                self.log.debug("%s: %s", query, values)
                try:
                    await cursor.execute(query, values)
                except psycopg.errors.IntegrityError:
                    await connection.rollback()
                    raise

                rowcount = int(cursor.rowcount or cursor.rownumber or 0)

                if cursor.pgresult and cursor.pgresult.status == psycopg.pq.ExecStatus.TUPLES_OK:
                    rows = await cursor.fetchall()
                else:
                    rows = []

                return rowcount, rows

    async def execute_query_dict(
        self, query: str, values: typing.Optional[list] = None
    ) -> typing.List[dict]:
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

    def acquire_connection(
        self,
    ) -> typing.Union[base_client.ConnectionWrapper, PoolConnectionWrapper]:
        return PoolConnectionWrapper(self)

    def _in_transaction(self) -> base_client.TransactionContext:
        return base_client.TransactionContextPooled(TransactionWrapper(self))


class TransactionWrapper(PsycopgClient, base_client.BaseTransactionWrapper):
    _connection: psycopg.AsyncConnection

    def __init__(self, connection: PsycopgClient) -> None:
        self._connection: psycopg.AsyncConnection = connection._connection
        self._lock = asyncio.Lock()
        self._trxlock = asyncio.Lock()
        self.log = connection.log
        self.connection_name = connection.connection_name
        self._finalized = False
        self._parent = connection

    def _in_transaction(self) -> base_client.TransactionContext:
        return base_client.NestedTransactionPooledContext(self)

    def acquire_connection(self) -> base_client.ConnectionWrapper:
        return base_client.ConnectionWrapper(self._lock, self)

    @postgres_client.translate_exceptions
    async def start(self) -> None:
        # We're not using explicit transactions here because psycopg takes care of that
        # automatically when autocommit is disabled.
        await self._connection.set_autocommit(False)

    async def commit(self) -> None:
        if self._finalized:
            raise exceptions.TransactionManagementError("Transaction already finalised")

        await self._connection.commit()
        await self._connection.set_autocommit(True)
        self._finalized = True

    async def rollback(self) -> None:
        if self._finalized:
            raise exceptions.TransactionManagementError("Transaction already finalised")

        await self._connection.rollback()
        await self._connection.set_autocommit(True)
        self._finalized = True
