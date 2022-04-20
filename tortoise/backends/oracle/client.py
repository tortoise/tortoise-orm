from typing import Any, SupportsInt

from pypika import OracleQuery

from tortoise.backends.base.client import TransactionContext, TransactionContextPooled
from tortoise.backends.odbc.client import ODBCClient, ODBCTransactionWrapper, translate_exceptions
from tortoise.backends.oracle.executor import OracleExecutor
from tortoise.backends.oracle.schema_generator import OracleSchemaGenerator


class OracleClient(ODBCClient):
    query_class = OracleQuery
    schema_generator = OracleSchemaGenerator
    executor_class = OracleExecutor

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
        self.password = password
        self.dsn = f"DRIVER={driver};DBQ={host}:{port};UID={user};PWD={password};"

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self))

    async def create_connection(self, with_db: bool) -> None:
        await super(OracleClient, self).create_connection(with_db=with_db)
        if with_db:
            await self.execute_query(f'ALTER SESSION SET CURRENT_SCHEMA = "{self.database}"')
        await self.execute_query("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD'")
        await self.execute_query(
            "ALTER SESSION SET NLS_TIMESTAMP_TZ_FORMAT = 'YYYY-MM-DD\"T\"HH24:MI:SSTZH:TZM'"
        )

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(
            f'CREATE USER "{self.database}" IDENTIFIED BY "{self.password}";GRANT ALL PRIVILEGES TO "{self.database}";'
        )
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f'DROP USER "{self.database}" CASCADE')
        await self.close()

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            await connection.execute(query, values)
            return 0


class TransactionWrapper(OracleClient, ODBCTransactionWrapper):
    def __init__(self, connection: ODBCClient) -> None:
        ODBCTransactionWrapper.__init__(self, connection=connection)
