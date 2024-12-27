from itertools import count
from typing import Any, Optional, SupportsInt

from pypika_tortoise.dialects import MSSQLQuery

from tortoise.backends.base.client import (
    Capabilities,
    NestedTransactionContext,
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
from tortoise.exceptions import TransactionManagementError


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
        return TransactionContextPooled(TransactionWrapper(self), self._pool_init_lock)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.execute(query, values)
                await cursor.execute("SELECT @@IDENTITY;")
                return (await cursor.fetchone())[0]


def _gen_savepoint_name(_c=count()) -> str:
    return f"tortoise_savepoint_{next(_c)}"


class TransactionWrapper(ODBCTransactionWrapper, MSSQLClient):
    def __init__(self, connection: ODBCClient) -> None:
        super().__init__(connection)
        self._savepoint: Optional[str] = None

    def _in_transaction(self) -> "TransactionContext":
        return NestedTransactionContext(TransactionWrapper(self))

    async def begin(self) -> None:
        await self._connection.execute("BEGIN TRANSACTION")
        await super().begin()

    async def savepoint(self) -> None:
        self._savepoint = _gen_savepoint_name()
        await self._connection.execute(f"SAVE TRANSACTION {self._savepoint}")

    async def savepoint_rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if self._savepoint is None:
            raise TransactionManagementError("No savepoint to rollback to")
        await self._connection.execute(f"ROLLBACK TRANSACTION {self._savepoint}")
        self._savepoint = None
        self._finalized = True

    async def release_savepoint(self) -> None:
        # MSSQL does not support releasing savepoints, so no action
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        if self._savepoint is None:
            raise TransactionManagementError("No savepoint to rollback to")
        self._savepoint = None
        self._finalized = True
