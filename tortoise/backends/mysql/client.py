from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from itertools import count
from typing import Any, SupportsInt, TypeVar

try:
    import asyncmy as mysql
    from asyncmy import errors
    from asyncmy.charset import charset_by_name
    from asyncmy.constants import COMMAND
except ImportError:
    import aiomysql as mysql
    from pymysql import err as errors
    from pymysql.charset import charset_by_name
    from pymysql.constants import COMMAND

from pypika_tortoise import MySQLQuery

from tortoise import timezone
from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    Capabilities,
    ConnectionWrapper,
    NestedTransactionContext,
    PoolConnectionWrapper,
    TransactionalDBClient,
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

T = TypeVar("T")
FuncType = Callable[..., Coroutine[None, None, T]]


def translate_exceptions(func: FuncType) -> FuncType:
    @wraps(func)
    async def translate_exceptions_(self, *args) -> T:
        try:
            return await func(self, *args)
        except (
            errors.OperationalError,
            errors.ProgrammingError,
            errors.DataError,
            errors.InternalError,
            errors.NotSupportedError,
        ) as exc:
            raise OperationalError(exc)
        except errors.IntegrityError as exc:
            raise IntegrityError(exc)

    return translate_exceptions_


class MySQLClient(BaseDBAsyncClient):
    query_class = MySQLQuery
    executor_class = MySQLExecutor
    schema_generator = MySQLSchemaGenerator
    capabilities = Capabilities(
        "mysql",
        requires_limit=True,
        inline_comment=True,
        support_index_hint=True,
        support_for_posix_regex_queries=True,
    )

    def __init__(
        self,
        *,
        user: str,
        password: str,
        database: str,
        host: str,
        port: SupportsInt,
        **kwargs: Any,
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
        self.extra.setdefault("sql_mode", "STRICT_TRANS_TABLES")
        self.charset = self.extra.pop("charset", "utf8mb4")
        self.pool_minsize = int(self.extra.pop("minsize", 1))
        self.pool_maxsize = int(self.extra.pop("maxsize", 5))

        self._template: dict = {}
        self._pool: mysql.Pool | None = None
        self._connection = None
        self._pool_init_lock = asyncio.Lock()

    async def create_connection(self, with_db: bool) -> None:
        if charset_by_name(self.charset) is None:
            raise DBConnectionError(f"Unknown charset {self.charset}")
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
            self._pool = await mysql.create_pool(password=self.password, **self._template)

            if isinstance(self._pool, mysql.Pool):
                async with self.acquire_connection() as connection:
                    async with connection.cursor() as cursor:
                        if self.storage_engine:
                            await cursor.execute(
                                f"SET default_storage_engine='{self.storage_engine}';"
                            )
                            if self.storage_engine.lower() != "innodb":  # pragma: nobranch
                                self.capabilities.__dict__["supports_transactions"] = False
                        hours = timezone.now().utcoffset().seconds / 3600  # type: ignore
                        tz = f"{int(hours):+d}:{int((hours % 1) * 60):02d}"
                        await cursor.execute(f"SET time_zone='{tz}';")
            self.log.debug("Created connection %s pool with params: %s", self._pool, self._template)
        except errors.OperationalError:
            raise DBConnectionError(f"Can't connect to MySQL server: {self._template}")

    async def _expire_connections(self) -> None:
        if self._pool:  # pragma: nobranch
            for conn in self._pool._free:
                conn._reader.set_exception(EOFError("EOF"))

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

    def acquire_connection(self) -> ConnectionWrapper | PoolConnectionWrapper:
        return PoolConnectionWrapper(self, self._pool_init_lock)

    def _in_transaction(self) -> TransactionContext:
        return TransactionContextPooled(TransactionWrapper(self), self._pool_init_lock)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.execute(query, values)
                return cursor.lastrowid  # return auto-generated id

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                if self.capabilities.supports_transactions:
                    await connection.begin()
                    try:
                        await cursor.executemany(query, values)
                    except Exception:
                        await connection.rollback()
                        raise
                    else:
                        await connection.commit()
                else:
                    await cursor.executemany(query, values)

    @translate_exceptions
    async def execute_query(self, query: str, values: list | None = None) -> tuple[int, list[dict]]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.execute(query, values)
                rows = await cursor.fetchall()
                if rows:
                    fields = [f.name for f in cursor._result.fields]
                    return cursor.rowcount, [dict(zip(fields, row)) for row in rows]
                return cursor.rowcount, []

    async def execute_query_dict(self, query: str, values: list | None = None) -> list[dict]:
        return (await self.execute_query(query, values))[1]

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:
                await cursor.execute(query)


class TransactionWrapper(MySQLClient, TransactionalDBClient):
    def __init__(self, connection: MySQLClient) -> None:
        self.connection_name = connection.connection_name
        self._connection: mysql.Connection = connection._connection
        self._lock = asyncio.Lock()
        self._savepoint: str | None = None
        self.log = connection.log
        self._finalized: bool = False
        self.fetch_inserted = connection.fetch_inserted
        self._parent = connection

    def _in_transaction(self) -> TransactionContext:
        return NestedTransactionContext(TransactionWrapper(self))

    def acquire_connection(self) -> ConnectionWrapper[mysql.Connection]:
        return ConnectionWrapper(self._lock, self)

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.executemany(query, values)

    @translate_exceptions
    async def begin(self) -> None:
        await self._connection.begin()
        self._finalized = False

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        self._finalized = True

    @translate_exceptions
    async def savepoint(self) -> None:
        self._savepoint = _gen_savepoint_name()
        await self._connection._execute_command(COMMAND.COM_QUERY, f"SAVEPOINT {self._savepoint}")
        await self._connection._read_ok_packet()

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        self._finalized = True

    async def savepoint_rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if self._savepoint is None:
            raise TransactionManagementError("No savepoint to rollback to")
        await self._connection._execute_command(
            COMMAND.COM_QUERY, f"ROLLBACK TO SAVEPOINT {self._savepoint}"
        )
        await self._connection._read_ok_packet()
        self._savepoint = None
        self._finalized = True

    async def release_savepoint(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if self._savepoint is None:
            raise TransactionManagementError("No savepoint to release")
        await self._connection._execute_command(
            COMMAND.COM_QUERY, f"RELEASE SAVEPOINT {self._savepoint}"
        )
        await self._connection._read_ok_packet()
        self._savepoint = None
        self._finalized = True


def _gen_savepoint_name(_c=count()) -> str:
    return f"tortoise_savepoint_{next(_c)}"
