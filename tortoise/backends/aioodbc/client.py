import asyncio
from functools import wraps
from typing import Any, Callable, List, Optional, SupportsInt, Tuple, TypeVar, Union

import aioodbc
import pyodbc
# from asyncpg.transaction import Transaction
import pypika
from pypika import OracleQuery as OrigOracleQuery


from tortoise.backends.aioodbc.executor import AioodbcExecutor
from tortoise.backends.aioodbc.schema_generator import AioodbcSchemaGenerator
from tortoise.backends.base.client import (
    BaseDBAsyncClient,
    BaseTransactionWrapper,
    Capabilities,
    ConnectionWrapper,
    NestedTransactionPooledContext,
    PoolConnectionWrapper,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.exceptions import (
    DBConnectionError,
    IntegrityError,
    OperationalError,
    TransactionManagementError,
)

FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


def translate_exceptions(func: F) -> F:
    @wraps(func)
    async def translate_exceptions_(self, *args):
        try:
            return await func(self, *args)
        except pyodbc.ProgrammingError as exc:
            raise OperationalError(exc)
        except pyodbc.IntegrityError as exc:
            raise IntegrityError(exc)
        except pyodbc.Error as exc:
            raise OperationalError(exc)
        # except pyodbc.erras exc:  # pragma: nocoverage
            # raise TransactionManagementError(exc)

    return translate_exceptions_  # type: ignore






from pypika import OracleQuery as OrigOracleQuery
from pypika.queries import QueryBuilder, Query
from pypika import Dialects


class OracleQueryBuilder(QueryBuilder):
    def __init__(self, **kwargs):
        super(OracleQueryBuilder, self).__init__(dialect=Dialects.ORACLE, **kwargs)

    def get_sql(self, *args, **kwargs):
        return super(OracleQueryBuilder, self).get_sql(
            *args, groupby_alias=False, **kwargs
        )

    def _limit_sql(self):
        return f' FETCH NEXT {self._limit} ROWS ONLY'


class OracleQuery(Query):
    """
    Defines a query class for use with Oracle.
    """

    @classmethod
    def _builder(cls, **kwargs):
        builder = OracleQueryBuilder(**kwargs)
        builder.QUOTE_CHAR = ""
        return builder



class AioodbcDBClient(BaseDBAsyncClient):
    DSN_TEMPLATE = "ODBC;Driver={{{driver}}};SERVER={c.host}:{c.port}/c.dataabase;UID={c.user};PWD={c.password};SCHEMA={c.schema};"
    query_class = OracleQuery
    executor_class = AioodbcExecutor
    schema_generator = AioodbcSchemaGenerator
    capabilities = Capabilities("oracle")

    def __init__(
        self, user: str, password: str, database: str, host: str, port: SupportsInt, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)  # make sure port is int type
        self.extra = kwargs.copy()
        self.schema = self.extra.pop("schema", None)
        self.extra.pop("connection_name", None)
        self.extra.pop("fetch_inserted", None)
        self.extra.pop("loop", None)
        self.extra.pop("connection_class", None)
        self.pool_minsize = int(self.extra.pop("minsize", 1))
        self.pool_maxsize = int(self.extra.pop("maxsize", 5))

        self._template: dict = {}
        self._pool: Optional[aioodbc.pool] = None
        self._connection = None

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "server": self.host,
            "port": self.port,
            "uid": self.user,
            "database": self.database if with_db else None,
            "min_size": self.pool_minsize,
            "max_size": self.pool_maxsize,
            "pwd": self.password,
            **self.extra
        }
        self._template["dsn"] = self.DSN_TEMPLATE.format(c=self, driver=self.extra['driver'])
        if self.schema:
            self._template["server_settings"] = {"search_path": self.schema}

        async def conn_attributes(conn):
            #conn.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
            #conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
            #conn.setdecoding(pyodbc.SQL_WMETADATA, encoding='utf-16le')
            #conn.setencoding(encoding='utf-16')
            pass
        try:
            self._pool = await aioodbc.create_pool(loop=None,
                                                   **self._template,
                                                   after_created=conn_attributes)
            self.log.debug("Created connection pool %s with params: %s", self._pool, self._template)
        except pyodbc.OperationalError:
            raise DBConnectionError(f"Can't establish connection to database {self.database}")
        # Set post-connection variables

    async def _expire_connections(self) -> None:
        if self._pool:  # pragma: nobranch
            await self._pool.expire_connections()

    async def _close(self) -> None:
        if self._pool:  # pragma: nobranch
            try:
                self._pool.close()
                await asyncio.wait_for(self._pool.wait_closed(), 10)
            except asyncio.TimeoutError:  # pragma: nocoverage
                self._pool.close()
            self._pool = None
            self.log.debug("Closed connection pool %s with params: %s", self._pool, self._template)

    async def close(self) -> None:
        await self._close()
        self._template.clear()

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f'CREATE DATABASE "{self.database}" OWNER "{self.user}"')
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        try:
            await self.execute_script(f'DROP DATABASE "{self.database}"')
        except pyodbc.ProgrammingError:  # pragma: nocoverage
            pass
        await self.close()

    def acquire_connection(self) -> Union["PoolConnectionWrapper", "ConnectionWrapper"]:
        return PoolConnectionWrapper(self._pool)

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self))

    @translate_exceptions
    async def execute_insert(self, query: str, values: list):
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
            async with connection.cursor() as cursor:
                params = [item for item in  [query, values] if item]
                await cursor.execute(*params)
                rows = await cursor.fetchall()
                if rows:
                    fields = [f[0].lower() for f in cursor.description]
                    return cursor.rowcount, [dict(zip(fields, row)) for row in rows]
                return cursor.rowcount, []

    @translate_exceptions
    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            if values:
                # TODO: Cache prepared statement
                return list(map(dict, await connection.fetch(query, *values)))
            return list(map(dict, await connection.fetch(query)))

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            await connection.execute(query)


class TransactionWrapper(AioodbcDBClient, BaseTransactionWrapper):
    def __init__(self, connection: AioodbcDBClient) -> None:
        self._connection: aioodbc.Connection = connection._connection
        self._lock = asyncio.Lock()
        self._trxlock = asyncio.Lock()
        self.log = connection.log
        self.connection_name = connection.connection_name
        self.transaction = None
        self._finalized = False
        self._parent = connection

    def _in_transaction(self) -> "TransactionContext":
        return NestedTransactionPooledContext(self)

    def acquire_connection(self) -> "ConnectionWrapper":
        return ConnectionWrapper(self._connection, self._lock)

    @translate_exceptions
    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            # TODO: Consider using copy_records_to_table instead
            await connection.executemany(query, values)

    @translate_exceptions
    async def start(self) -> None:
        self.transaction = self._connection.transaction()
        await self.transaction.start()

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self.transaction.commit()
        self._finalized = True

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self.transaction.rollback()
        self._finalized = True
