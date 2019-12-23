import asyncio
import logging
from typing import Any, List, Optional, Sequence, Tuple, Type, Union

from pypika import Query

from tortoise.backends.base.executor import BaseExecutor
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.exceptions import TransactionManagementError
from tortoise.transactions import current_transaction_map


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

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        raise NotImplementedError()  # pragma: nocoverage

    def _in_transaction(self) -> "TransactionContext":
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_insert(self, query: str, values: list) -> Any:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_query(
        self, query: str, values: Optional[list] = None
    ) -> Tuple[int, Sequence[dict]]:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_script(self, query: str) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_many(self, query: str, values: List[list]) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_query_dict(self, query: str, values: Optional[list] = None) -> List[dict]:
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


class TransactionContext:
    __slots__ = ("connection", "connection_name", "token", "lock")

    def __init__(self, connection) -> None:
        self.connection = connection
        self.connection_name = connection.connection_name
        self.lock = getattr(connection, "_trxlock", None)

    async def __aenter__(self):
        await self.lock.acquire()
        current_transaction = current_transaction_map[self.connection_name]
        self.token = current_transaction.set(self.connection)
        await self.connection.start()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self.connection._finalized:
            if exc_type:
                # Can't rollback a transaction that already failed.
                if exc_type is not TransactionManagementError:
                    await self.connection.rollback()
            else:
                await self.connection.commit()
        current_transaction_map[self.connection_name].reset(self.token)
        self.lock.release()


class TransactionContextPooled(TransactionContext):
    __slots__ = ("connection", "connection_name", "token")

    async def __aenter__(self):
        current_transaction = current_transaction_map[self.connection_name]
        self.token = current_transaction.set(self.connection)
        self.connection._connection = await self.connection._parent._pool.acquire()
        await self.connection.start()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self.connection._finalized:
            if exc_type:
                # Can't rollback a transaction that already failed.
                if exc_type is not TransactionManagementError:
                    await self.connection.rollback()
            else:
                await self.connection.commit()
        current_transaction_map[self.connection_name].reset(self.token)
        if self.connection._parent._pool:
            await self.connection._parent._pool.release(self.connection._connection)


class NestedTransactionContext(TransactionContext):
    async def __aenter__(self):
        await self.connection.start()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self.connection._finalized:
            if exc_type:
                # Can't rollback a transaction that already failed.
                if exc_type is not TransactionManagementError:
                    await self.connection.rollback()
            else:
                await self.connection.commit()


class PoolConnectionWrapper:
    def __init__(self, pool) -> None:
        self.pool = pool
        self.connection = None

    async def __aenter__(self):
        # get first available connection
        self.connection = await self.pool.acquire()
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # release the connection back to the pool
        await self.pool.release(self.connection)


class BaseTransactionWrapper:
    async def start(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    def release(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def rollback(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def commit(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage
