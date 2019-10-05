import asyncio
import logging
from typing import Any, List, Optional, Sequence, Type

from pypika import Query

from tortoise.backends.base.executor import BaseExecutor
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.exceptions import TransactionManagementError


class Capabilities:
    """
    DB Client Capabilities indicates the supported feature-set,
    and is also used to note common workarounds to defeciences.

    Defaults are set with the following standard:

    * Defeciences: assume it is working right.
    * Features: assume it doesn't have it.

    Fields:

    ``dialect``:
        Dialect name of the DB Client driver.
    ``requires_limit``:
        Indicates that this DB requires a ``LIMIT`` statement for an ``OFFSET`` statement to work.
    ``inline_comment``:
        Indicates that comments should be rendered in line with the DDL statement,
        and not as a separate statement.
    ``supports_transactions``:
        Indicates that this DB supports transactions.
    """

    def __init__(
        self,
        dialect: str,
        *,
        # Is the connection a Daemon?
        daemon: bool = True,
        # Deficiencies to work around:
        requires_limit: bool = False,
        inline_comment: bool = False,
        supports_transactions: bool = True,
    ) -> None:
        super().__setattr__("_mutable", True)

        self.dialect = dialect
        self.daemon = daemon
        self.requires_limit = requires_limit
        self.inline_comment = inline_comment
        self.supports_transactions = supports_transactions

        super().__setattr__("_mutable", False)

    def __setattr__(self, attr, value):
        if not getattr(self, "_mutable", False):
            raise AttributeError(attr)
        return super().__setattr__(attr, value)

    def __str__(self) -> str:
        return str(self.__dict__)


class BaseDBAsyncClient:
    query_class: Type[Query] = Query
    executor_class: Type[BaseExecutor] = BaseExecutor
    schema_generator: Type[BaseSchemaGenerator] = BaseSchemaGenerator
    capabilities: Capabilities = Capabilities("")

    def __init__(self, connection_name: str, fetch_inserted: bool = True, **kwargs) -> None:
        self.log = logging.getLogger("db_client")
        self.connection_name = connection_name
        self.fetch_inserted = fetch_inserted

    async def create_connection(self, with_db: bool) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def db_create(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def db_delete(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    def acquire_connection(self) -> "ConnectionWrapper":
        raise NotImplementedError()  # pragma: nocoverage

    def _in_transaction(self) -> "BaseTransactionWrapper":
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_insert(self, query: str, values: list) -> Any:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_query(self, query: str, values: Optional[list] = None) -> Sequence[dict]:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_script(self, query: str) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_many(self, query: str, values: List[list]) -> None:
        raise NotImplementedError()  # pragma: nocoverage


class ConnectionWrapper:
    __slots__ = ("connection", "lock")

    def __init__(self, connection, lock: asyncio.Lock) -> None:
        self.connection = connection
        self.lock: asyncio.Lock = lock

    async def __aenter__(self):
        await self.lock.acquire()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.lock.release()


class BaseTransactionWrapper:
    async def start(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    def release(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def rollback(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def commit(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            if issubclass(exc_type, TransactionManagementError):
                self.release()
            else:
                await self.rollback()
        else:
            await self.commit()
