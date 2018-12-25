import logging
from functools import wraps
from typing import List, Optional, SupportsInt  # noqa

import aiomysql
import pymysql
from pypika import MySQLQuery

from tortoise.backends.base.client import (BaseDBAsyncClient, BaseTransactionWrapper, Capabilities,
                                           ConnectionWrapper)
from tortoise.backends.mysql.executor import MySQLExecutor
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.exceptions import (DBConnectionError, IntegrityError, OperationalError,
                                 TransactionManagementError)
from tortoise.transactions import current_transaction_map

logger = logging.getLogger(__name__)


def translate_exceptions(func):
    @wraps(func)
    async def wrapped(self, query, *args):
        try:
            return await func(self, query, *args)
        except (pymysql.err.OperationalError, pymysql.err.ProgrammingError,
                pymysql.err.DataError, pymysql.err.InternalError,
                pymysql.err.NotSupportedError) as exc:
            raise OperationalError(exc)
        except pymysql.err.IntegrityError as exc:
            raise IntegrityError(exc)
    return wrapped


class MysQLConnectionWrapper(ConnectionWrapper):
    __slots__ = ('pool', )

    def __init__(self, pool) -> None:
        super().__init__(None)
        self.pool = pool  # type: aiomysql.Pool

    async def __aenter__(self):
        self.connection = await self.pool.acquire()
        logger.debug('Acquired connection %s', self.connection)
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.debug('Released connection %s', self.connection)
        self.pool.release(self.connection)


class MySQLClient(BaseDBAsyncClient):
    query_class = MySQLQuery
    executor_class = MySQLExecutor
    schema_generator = MySQLSchemaGenerator
    capabilities = Capabilities('mysql', safe_indexes=False, requires_limit=True)

    def __init__(self, user: str, password: str, database: str, host: str, port: SupportsInt,
                 minsize: SupportsInt, maxsize: SupportsInt, **kwargs) -> None:
        super().__init__(**kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)  # make sure port is int type
        self.minsize = int(minsize)
        self.maxsize = int(maxsize)

        self._connection = None  # Type: Optional[aiomysql.Pool]

        self._transaction_class = type(
            'TransactionWrapper', (TransactionWrapper, self.__class__), {}
        )

    async def create_connection(self, with_db: bool) -> None:
        template = {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'db': self.database if with_db else None,
            'minsize': self.minsize,
            'maxsize': self.maxsize,
            'autocommit': True,
        }

        try:
            self._connection = await aiomysql.create_pool(**template)
            self.log.debug(
                'Created pool %s with params: user=%s database=%s host=%s port=%s minsize=%s'
                ' maxsize=%s', self._connection, self.user, self.database, self.host, self.port,
                self.minsize, self.maxsize
            )
        except pymysql.err.OperationalError:
            raise DBConnectionError(
                'user={user} database={database} host={host} port={port} minsize={minsize}'
                ' maxsize={maxsize}'.format(
                    user=self.user, database=self.database, host=self.host, port=self.port,
                    minsize=self.minsize, maxsize=self.maxsize
                )
            )

    async def close(self) -> None:
        if self._connection:  # pragma: nobranch
            self._connection.close()
            await self._connection.wait_closed()
            self.log.debug(
                'Closed pool %s with params: user=%s database=%s host=%s port=%s minsize=%s'
                ' maxsize=%s', self._connection, self.user, self.database, self.host, self.port,
                self.minsize, self.maxsize
            )
            self._connection = None

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(
            'CREATE DATABASE {}'.format(self.database)
        )
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        try:
            await self.execute_script('DROP DATABASE {}'.format(self.database))
        except pymysql.err.DatabaseError:  # pragma: nocoverage
            pass
        await self.close()

    def acquire_connection(self) -> ConnectionWrapper:
        return MysQLConnectionWrapper(self._connection)

    def _in_transaction(self):
        return self._transaction_class(self.connection_name, self._connection)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        async with self.acquire_connection() as connection:
            self.log.debug('%s: %s', query, values)
            async with connection.cursor() as cursor:
                # TODO: Use prepared statement, and cache it
                await cursor.execute(query, values)
                return cursor.lastrowid  # return auto-generated id

    @translate_exceptions
    async def execute_query(self, query: str) -> List[aiomysql.DictCursor]:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query)
                return await cursor.fetchall()

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            async with connection.cursor() as cursor:
                await cursor.execute(query)


class TransactionWrapper(MySQLClient, BaseTransactionWrapper):
    def __init__(self, connection_name, pool):
        self.connection_name = connection_name
        self._pool = pool
        self.log = logging.getLogger('db_client')
        self._transaction_class = self.__class__
        self._finalized = False
        self._old_context_value = None

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._connection)

    async def start(self):
        self._connection = await self._pool.acquire()
        self.log.debug('Acquired connection for transaction %s', self._connection)
        await self._connection.begin()
        current_transaction = current_transaction_map[self.connection_name]
        self._old_context_value = current_transaction.get()
        current_transaction.set(self)

    async def commit(self):
        if self._finalized:
            raise TransactionManagementError('Transaction already finalised')
        self._finalized = True
        await self._connection.commit()
        self.log.debug('Released connection for committed transaction %s', self._connection)
        self._pool.release(self._connection)
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def rollback(self):
        if self._finalized:
            raise TransactionManagementError('Transaction already finalised')
        self._finalized = True
        await self._connection.rollback()
        self.log.debug('Released connection for rolled back transaction %s', self._connection)
        self._pool.release(self._connection)
        current_transaction_map[self.connection_name].set(self._old_context_value)
