from __future__ import annotations

import abc
import asyncio
from collections.abc import Sequence
from typing import Any, Generic, Type, TypeVar, cast

from pypika_tortoise import Query

from tortoise.backends.base.executor import BaseExecutor
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.connection import connections
from tortoise.exceptions import TransactionManagementError
from tortoise.log import db_client_logger

T_conn = TypeVar("T_conn")  # Instance of client connection, such as: asyncpg.Connection()


class Capabilities:
    """
    DB Client Capabilities indicates the supported feature-set,
    and is also used to note common workarounds to deficiencies.

    Defaults are set with the following standard:

    * Deficiencies: assume it is working right.
    * Features: assume it doesn't have it.

    :param dialect: Dialect name of the DB Client driver.
    :param daemon: Is the DB an external Daemon we connect to?
    :param requires_limit:  Indicates that this DB requires a ``LIMIT`` statement for
        an ``OFFSET`` statement to work.
    :param inline_comment: Indicates that comments should be rendered in line with the
        DDL statement, and not as a separate statement.
    :param supports_transactions: Indicates that this DB supports transactions.
    :param support_for_update: Indicates that this DB supports SELECT ... FOR UPDATE SQL statement.
    :param support_index_hint: Support force index or use index.
    :param support_update_limit_order_by: support update/delete with limit and order by.
    :param: support_for_posix_regex_queries: indicated if the db supports posix regex queries
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
        support_for_update: bool = True,
        # Support force index or use index?
        support_index_hint: bool = False,
        # support update/delete with limit and order by
        support_update_limit_order_by: bool = True,
        support_for_posix_regex_queries: bool = False,
    ) -> None:
        super().__setattr__("_mutable", True)

        self.dialect = dialect
        self.daemon = daemon
        self.requires_limit = requires_limit
        self.inline_comment = inline_comment
        self.supports_transactions = supports_transactions
        self.support_for_update = support_for_update
        self.support_index_hint = support_index_hint
        self.support_update_limit_order_by = support_update_limit_order_by
        self.support_for_posix_regex_queries = support_for_posix_regex_queries
        super().__setattr__("_mutable", False)

    def __setattr__(self, attr: str, value: Any) -> None:
        if not getattr(self, "_mutable", False):
            raise AttributeError(attr)
        super().__setattr__(attr, value)

    def __str__(self) -> str:
        return str(self.__dict__)


class BaseDBAsyncClient(abc.ABC):
    """
    Base class for containing a DB connection.

    Parameters get passed as kwargs, and is mostly driver specific.

    .. attribute:: query_class
        :annotation: Type[pypika_tortoise.Query]

        The PyPika Query dialect (low level dialect)

    .. attribute:: executor_class
        :annotation: Type[BaseExecutor]

        The executor dialect class (high level dialect)

    .. attribute:: schema_generator
        :annotation: Type[BaseSchemaGenerator]

        The DDL schema generator

    .. attribute:: capabilities
        :annotation: Capabilities

        Contains the connection capabilities
    """

    _connection: Any
    _parent: "BaseDBAsyncClient"
    _pool: Any
    connection_name: str
    query_class: Type[Query] = Query
    executor_class: Type[BaseExecutor] = BaseExecutor
    schema_generator: Type[BaseSchemaGenerator] = BaseSchemaGenerator
    capabilities: Capabilities = Capabilities("")

    def __init__(self, connection_name: str, fetch_inserted: bool = True, **kwargs: Any) -> None:
        self.log = db_client_logger
        self.connection_name = connection_name
        self.fetch_inserted = fetch_inserted

    async def create_connection(self, with_db: bool) -> None:
        """
        Establish a DB connection.

        :param with_db: If True, then select the DB to use, else use default.
            Use case for this is to create/drop a database.
        """
        raise NotImplementedError()  # pragma: nocoverage

    async def close(self) -> None:
        """
        Closes the DB connection.
        """
        raise NotImplementedError()  # pragma: nocoverage

    async def db_create(self) -> None:
        """
        Created the database in the server. Typically only called by the test runner.

        Need to have called ``create_connection()``` with parameter ``with_db=False`` set to
        use the default connection instead of the configured one, else you would get errors
        indicating the database doesn't exist.
        """
        raise NotImplementedError()  # pragma: nocoverage

    async def db_delete(self) -> None:
        """
        Delete the database from the Server. Typically only called by the test runner.

        Need to have called ``create_connection()``` with parameter ``with_db=False`` set to
        use the default connection instead of the configured one, else you would get errors
        indicating the database is in use.
        """
        raise NotImplementedError()  # pragma: nocoverage

    def acquire_connection(self) -> "ConnectionWrapper" | "PoolConnectionWrapper":
        """
        Acquires a connection from the pool.
        Will return the current context connection if already in a transaction.
        """
        raise NotImplementedError()  # pragma: nocoverage

    def _in_transaction(self) -> "TransactionContext":
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_insert(self, query: str, values: list) -> Any:
        """
        Executes a RAW SQL insert statement, with provided parameters.

        :param query: The SQL string, pre-parametrized for the target DB dialect.
        :param values: A sequence of positional DB parameters.
        :return: The primary key if it is generated by the DB.
            (Currently only integer autonumber PK's)
        """
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_query(
        self, query: str, values: list | None = None
    ) -> tuple[int, Sequence[dict]]:
        """
        Executes a RAW SQL query statement, and returns the resultset.

        :param query: The SQL string, pre-parametrized for the target DB dialect.
        :param values: A sequence of positional DB parameters.
        :return: A tuple of: (The number of rows affected, The resultset)
        """
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_script(self, query: str) -> None:
        """
        Executes a RAW SQL script with multiple statements, and returns nothing.

        :param query: The SQL string, which will be passed on verbatim.
            Semicolons is supported here.
        """
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_many(self, query: str, values: list[list]) -> None:
        """
        Executes a RAW bulk insert statement, like execute_insert, but returns no data.

        :param query: The SQL string, pre-parametrized for the target DB dialect.
        :param values: A sequence of positional DB parameters.
        """
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_query_dict(self, query: str, values: list | None = None) -> list[dict]:
        """
        Executes a RAW SQL query statement, and returns the resultset as a list of dicts.

        :param query: The SQL string, pre-parametrized for the target DB dialect.
        :param values: A sequence of positional DB parameters.
        """
        raise NotImplementedError()  # pragma: nocoverage


class TransactionalDBClient(BaseDBAsyncClient, abc.ABC):
    """An interface of the DB client that supports transactions."""

    _finalized: bool = False

    @abc.abstractmethod
    async def begin(self) -> None: ...

    @abc.abstractmethod
    async def savepoint(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...

    @abc.abstractmethod
    async def savepoint_rollback(self) -> None: ...

    @abc.abstractmethod
    async def commit(self) -> None: ...

    @abc.abstractmethod
    async def release_savepoint(self) -> None: ...


class ConnectionWrapper(Generic[T_conn]):
    """Wraps the connections with a lock to facilitate safe concurrent access when using
    asyncio.gather, TaskGroup, or similar."""

    __slots__ = ("connection", "_lock", "client")

    def __init__(self, lock: asyncio.Lock, client: BaseDBAsyncClient) -> None:
        self._lock: asyncio.Lock = lock
        self.client = client
        self.connection: T_conn = client._connection

    async def ensure_connection(self) -> None:
        if not self.connection:
            await self.client.create_connection(with_db=True)
            self.connection = self.client._connection

    async def __aenter__(self) -> T_conn:
        await self._lock.acquire()
        await self.ensure_connection()
        return self.connection

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._lock.release()


class TransactionContext(Generic[T_conn]):
    """A context manager interface for transactions. It is returned from in_transaction
    and _in_transaction."""

    client: TransactionalDBClient

    @abc.abstractmethod
    async def __aenter__(self) -> T_conn: ...

    @abc.abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...


class TransactionContextPooled(TransactionContext):
    "A version of TransactionContext that uses a pool to acquire connections."

    __slots__ = ("client", "connection_name", "token", "_pool_init_lock")

    def __init__(self, client: TransactionalDBClient, pool_init_lock: asyncio.Lock) -> None:
        self.client = client
        self.connection_name = client.connection_name
        self._pool_init_lock = pool_init_lock

    async def ensure_connection(self) -> None:
        if not self.client._parent._pool:
            # a safeguard against multiple concurrent tasks trying to initialize the pool
            async with self._pool_init_lock:
                if not self.client._parent._pool:
                    await self.client._parent.create_connection(with_db=True)

    async def __aenter__(self) -> TransactionalDBClient:
        await self.ensure_connection()
        # Set the context variable so the current task is always seeing a
        # TransactionWrapper conneciton.
        self.token = connections.set(self.connection_name, self.client)
        self.client._connection = await self.client._parent._pool.acquire()
        await self.client.begin()
        return self.client

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            if not self.client._finalized:
                if exc_type:
                    # Can't rollback a transaction that already failed.
                    if exc_type is not TransactionManagementError:
                        await self.client.rollback()
                else:
                    await self.client.commit()
        finally:
            if self.client._parent._pool:
                await self.client._parent._pool.release(self.client._connection)
            connections.reset(self.token)


class NestedTransactionContext(TransactionContext):
    __slots__ = ("client", "connection_name")

    def __init__(self, client: TransactionalDBClient) -> None:
        self.client = client
        self.connection_name = client.connection_name

    async def __aenter__(self) -> TransactionalDBClient:
        await self.client.savepoint()
        return self.client

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if not self.client._finalized:
            if exc_type:
                # Can't rollback a transaction that already failed.
                if exc_type is not TransactionManagementError:
                    await self.client.savepoint_rollback()
            else:
                await self.client.release_savepoint()


class PoolConnectionWrapper(Generic[T_conn]):
    """Class to manage acquiring from and releasing connections to a pool."""

    __slots__ = ("client", "connection", "_pool_init_lock")

    def __init__(self, client: BaseDBAsyncClient, pool_init_lock: asyncio.Lock) -> None:
        self.client = client
        self.connection: T_conn | None = None
        self._pool_init_lock = pool_init_lock

    async def ensure_connection(self) -> None:
        if not self.client._pool:
            # a safeguard against multiple concurrent tasks trying to initialize the pool
            async with self._pool_init_lock:
                if not self.client._pool:
                    await self.client.create_connection(with_db=True)

    async def __aenter__(self) -> T_conn:
        await self.ensure_connection()
        # get first available connection. If none available, wait until one is released
        self.connection = await self.client._pool.acquire()
        return cast(T_conn, self.connection)

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # release the connection back to the pool
        await self.client._pool.release(self.connection)
