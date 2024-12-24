import datetime
import functools
from typing import TYPE_CHECKING, Any, SupportsInt, Union

import pyodbc
import pytz

try:
    from ciso8601 import parse_datetime
except ImportError:  # pragma: nocoverage
    from iso8601 import parse_date

    parse_datetime = functools.partial(parse_date, default_timezone=None)
from pypika import OracleQuery

from tortoise.backends.base.client import (
    Capabilities,
    ConnectionWrapper,
    PoolConnectionWrapper,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.backends.odbc.client import (
    ODBCClient,
    ODBCTransactionWrapper,
    translate_exceptions,
)
from tortoise.backends.oracle.executor import OracleExecutor
from tortoise.backends.oracle.schema_generator import OracleSchemaGenerator

if TYPE_CHECKING:  # pragma: nocoverage
    import asyncodbc  # pylint: disable=W0611


class OracleClient(ODBCClient):
    query_class = OracleQuery
    schema_generator = OracleSchemaGenerator
    executor_class = OracleExecutor
    capabilities = Capabilities(dialect="oracle")

    def __init__(
        self,
        *,
        user: str,
        password: str,
        host: str,
        port: SupportsInt,
        driver: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.user = user.upper()
        self.password = password
        dbq = f"{host}:{port}"
        if self.database:
            dbq += f"/{self.database}"
        self.dsn = f"DRIVER={driver};DBQ={dbq};UID={user};PWD={password};"

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self), self._pool_init_lock)

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return OraclePoolConnectionWrapper(self, self._pool_init_lock)

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f'CREATE USER "{self.database}" IDENTIFIED BY "{self.password}"')
        await self.execute_script(f'GRANT ALL PRIVILEGES TO "{self.database}"')
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        try:
            await self.execute_script(f'DROP USER "{self.database}" CASCADE')
        except pyodbc.Error as e:
            if "does not exist" not in str(e):
                raise
        await self.close()

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:
                for q in query.split(";"):
                    if not q.strip():
                        continue
                    await cursor.execute(q)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            await connection.execute(query, values)
            return 0


class OraclePoolConnectionWrapper(PoolConnectionWrapper):
    def _timestamp_convert(self, value: bytes) -> datetime.date:
        try:
            return parse_datetime(value.decode()).date()
        except ValueError:
            return parse_datetime(value.decode()[:-32]).astimezone(tz=pytz.utc)

    async def __aenter__(self) -> "asyncodbc.Connection":
        connection = await super().__aenter__()
        if getattr(self.client, "database", False) and not hasattr(connection, "current_schema"):
            await connection.execute(f'ALTER SESSION SET CURRENT_SCHEMA = "{self.client.user}"')
            await connection.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD'")
            await connection.execute(
                "ALTER SESSION SET NLS_TIMESTAMP_TZ_FORMAT = 'YYYY-MM-DD\"T\"HH24:MI:SSTZH:TZM'"
            )
            await connection.add_output_converter(
                pyodbc.SQL_TYPE_TIMESTAMP, self._timestamp_convert
            )
            setattr(connection, "current_schema", self.client.user)
        return connection


class TransactionWrapper(ODBCTransactionWrapper, OracleClient):
    async def begin(self) -> None:
        await self._connection.execute("SET TRANSACTION READ WRITE")
        await super().begin()
