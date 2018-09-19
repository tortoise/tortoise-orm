import logging

import asyncpg
from pypika import PostgreSQLQuery

from tortoise.backends.asyncpg.executor import AsyncpgExecutor
from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
from tortoise.backends.base.client import (BaseDBAsyncClient, BaseTransactionWrapper,
                                           ConnectionWrapper, SingleConnectionWrapper)
from tortoise.exceptions import (ConfigurationError, DBConnectionError, IntegrityError,
                                 OperationalError, TransactionManagementError)
from tortoise.transactions import current_transaction_map


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
        self.port = int(port)  # make sure port is int type

        self.dsn = self.DSN_TEMPLATE.format(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )
        self._db_pool = None
        self._connection = None

        self._transaction_class = type(
            'TransactionWrapper', (TransactionWrapper, self.__class__), {}
        )

    async def create_connection(self):
        try:
            if not self.single_connection:
                self._db_pool = await asyncpg.create_pool(self.dsn)
            else:
                self._connection = await asyncpg.connect(self.dsn)
            self.log.debug(
                'Created connection with params: '
                'user={user} database={database} host={host} port={port}'.format(
                    user=self.user, database=self.database, host=self.host, port=self.port
                )
            )
        except asyncpg.InvalidCatalogNameError:
            raise DBConnectionError("Can't establish connection to database {}".format(
                self.database
            ))

    async def close(self):
        if not self.single_connection:
            await self._db_pool.close()
        else:
            await self._connection.close()

    async def db_create(self):
        single_connection = self.single_connection
        self.single_connection = True
        self._connection = await asyncpg.connect(self.DSN_TEMPLATE.format(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=''
        ))
        await self.execute_script(
            'CREATE DATABASE "{}" OWNER "{}"'.format(self.database, self.user)
        )
        await self._connection.close()
        self.single_connection = single_connection

    async def db_delete(self):
        single_connection = self.single_connection
        self.single_connection = True
        self._connection = await asyncpg.connect(self.DSN_TEMPLATE.format(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=''
        ))
        try:
            await self.execute_script('DROP DATABASE "{}"'.format(self.database))
        except asyncpg.InvalidCatalogNameError:
            pass
        await self._connection.close()
        self.single_connection = single_connection

    def acquire_connection(self):
        if not self.single_connection:
            return self._db_pool.acquire()
        else:
            return ConnectionWrapper(self._connection)

    def _in_transaction(self):
        if self.single_connection:
            return self._transaction_class(self.connection_name, connection=self._connection)
        else:
            return self._transaction_class(self.connection_name, pool=self._db_pool)

    async def execute_query(self, query):
        try:
            async with self.acquire_connection() as connection:
                self.log.debug(query)
                return await connection.fetch(query)
        except asyncpg.exceptions.SyntaxOrAccessError as exc:
            raise OperationalError(exc)
        except asyncpg.exceptions.IntegrityConstraintViolationError as exc:
            raise IntegrityError(exc)

    async def get_single_connection(self):
        if self.single_connection:
            return self._single_connection_class(self.connection_name, self._connection)
        else:
            connection = await self._db_pool._acquire(None)
            return self._single_connection_class(self.connection_name, connection)

    async def release_single_connection(self, single_connection):
        if not self.single_connection:
            await self._db_pool.release(single_connection.connection)

    async def execute_script(self, script):
        try:
            async with self.acquire_connection() as connection:
                self.log.debug(script)
                await connection.execute(script)
        except asyncpg.exceptions.SyntaxOrAccessError as exc:
            raise OperationalError(exc)
        except asyncpg.exceptions.IntegrityConstraintViolationError as exc:
            raise IntegrityError(exc)


class TransactionWrapper(AsyncpgDBClient, BaseTransactionWrapper):
    def __init__(self, connection_name, pool=None, connection=None):
        if pool and connection:
            raise ConfigurationError('You must pass either connection or pool')
        self._connection = connection
        self.log = logging.getLogger('db_client')
        self._pool = pool
        self.single_connection = True
        self._single_connection_class = type(
            'SingleConnectionWrapper', (SingleConnectionWrapper, self.__class__), {}
        )
        self._transaction_class = self.__class__
        self._old_context_value = None
        self.connection_name = connection_name

    def acquire_connection(self):
        return ConnectionWrapper(self._connection)

    async def _get_connection(self):
        return await self._pool._acquire(None)

    async def start(self):
        if not self._connection:
            self._connection = await self._get_connection()
        self.transaction = self._connection.transaction()
        await self.transaction.start()
        current_transaction = current_transaction_map[self.connection_name]
        self._old_context_value = current_transaction.get()
        current_transaction.set(self)

    async def commit(self):
        try:
            await self.transaction.commit()
        except asyncpg.exceptions._base.InterfaceError as exc:
            raise TransactionManagementError(exc)
        if self._pool:
            await self._pool.release(self._connection)
            self._connection = None
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def rollback(self):
        try:
            await self.transaction.rollback()
        except asyncpg.exceptions._base.InterfaceError as exc:
            raise TransactionManagementError(exc)
        if self._pool:
            await self._pool.release(self._connection)
            self._connection = None
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
