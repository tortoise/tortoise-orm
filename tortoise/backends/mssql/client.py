from typing import Any, SupportsInt

from pypika.dialects import MSSQLQuery

from tortoise.backends.base.client import (
    Capabilities,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.backends.mssql.executor import MSSQLExecutor
from tortoise.backends.mssql.schema_generator import MSSQLSchemaGenerator
from tortoise.backends.odbc.client import (
    ODBCClient,
    ODBCTransactionWrapper,
    translate_exceptions,
)


class MSSQLClient(ODBCClient):
    query_class = MSSQLQuery
    schema_generator = MSSQLSchemaGenerator
    executor_class = MSSQLExecutor
    capabilities = Capabilities(
        "mssql", support_update_limit_order_by=False, support_for_update=False
    )

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
        self.dsn = f"DRIVER={driver};SERVER={host},{port};UID={user};PWD={password};"

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self))

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.execute(query, values)
                await cursor.execute("SELECT @@IDENTITY;")
                return (await cursor.fetchone())[0]


class TransactionWrapper(ODBCTransactionWrapper, MSSQLClient):
    async def start(self) -> None:
        await self._connection.execute("BEGIN TRANSACTION")
        await super().start()
