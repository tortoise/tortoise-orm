import logging

import asyncio
import asyncpg
from datetime import date

from aenum import Enum
from pypika import PostgreSQLQuery
from pypika.terms import ValueWrapper, basestring

from tortoise.backends.asyncpg.executor import AsyncpgExecutor
from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
from tortoise.backends.base.client import BaseDBAsyncClient, ConnectionWrapper, SingleConnectionWrapper


class AsyncpgDBClient(BaseDBAsyncClient):
    DSN_TEMPLATE = 'postgres://{user}:{password}@{host}:{port}/{database}'
    query_class = PostgreSQLQuery
    executor_class = AsyncpgExecutor
    schema_generator = AsyncpgSchemaGenerator

    def __init__(self, user, password, database, host, port, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port

        self.dsn = self.DSN_TEMPLATE.format(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )
        self._db_pool = None
        self._connection = None

        self._transaction_class = type('TransactionWrapper', (TransactionWrapper, self.__class__), {})

    async def create_connection(self):
        if not self.single_connection:
            self._db_pool = await asyncpg.create_pool(self.dsn)
        else:
            self._connection = await asyncpg.connect(self.dsn)
        self.log.debug(
            'Created connection with params: '
            'user={user} database={database} host={host} port={port}'.format(
                user=self.user,
                database=self.database,
                host=self.host,
                port=self.port
            )
        )

    async def close(self):
        if not self.single_connection:
            await self._db_pool.close()
        else:
            await self._connection.close()

    def acquire_connection(self):
        if not self.single_connection:
            return self._db_pool.acquire()
        else:
            return ConnectionWrapper(self._connection)

    def in_transaction(self):
        if self.single_connection:
            return self._transaction_class(connection=self._connection)
        else:
            return self._transaction_class(pool=self._db_pool)

    async def execute_query(self, query):
        async with self.acquire_connection() as connection:
            self.log.debug(query)
            rows = await connection.fetch(query)
            return rows

    async def get_single_connection(self):
        if self.single_connection:
            return self._single_connection_class(self._connection, self)
        else:
            connection = await self._db_pool._acquire(None)
            return self._single_connection_class(connection, self)

    async def release_single_connection(self, single_connection):
        if not self.single_connection:
            await self._db_pool.release(single_connection.connection)

    async def execute_script(self, script):
        async with self.acquire_connection() as connection:
            self.log.debug(script)
            await connection.execute(script)


class TransactionWrapper(AsyncpgDBClient):
    def __init__(self, pool=None, connection=None):
        assert bool(pool) != bool(connection), 'You must pass either connection or pool'
        self._connection = connection
        self.log = logging.getLogger('db_client')
        self._pool = pool
        self.single_connection = True
        self._single_connection_class = type(
            'SingleConnectionWrapper',
            (SingleConnectionWrapper, self.__class__),
            {}
        )
        self._transaction_class = self.__class__

    def acquire_connection(self):
        return ConnectionWrapper(self._connection)

    async def _get_connection(self):
        return await self._pool._acquire(None)

    async def start(self):
        if not self._connection:
            self._connection = await self._get_connection()
        self.transaction = self._connection.transaction()
        await self.transaction.start()

    async def commit(self):
        await self.transaction.commit()
        if self._pool:
            await self._pool.release(self._connection)
            self._connection = None

    async def rollback(self):
        await self.transaction.rollback()
        if self._pool:
            await self._pool.release(self._connection)
            self._connection = None

    async def __aenter__(self):
        if not self._connection:
            self._connection = await self._get_connection()
        self.transaction = self._connection.transaction()
        await self.transaction.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.transaction.rollback()
            if self._pool:
                await self._pool.release(self._connection)
                self._connection = None
            return False
        await self.transaction.commit()
        if self._pool:
            await self._pool.release(self._connection)
            self._connection = None
