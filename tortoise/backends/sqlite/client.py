import logging
import sqlite3

import aiosqlite

from tortoise import BaseDBAsyncClient
from tortoise.backends.base.client import ConnectionWrapper, SingleConnectionWrapper
from tortoise.backends.sqlite.executor import SqliteExecutor
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator


class SqliteClient(BaseDBAsyncClient):
    executor_class = SqliteExecutor
    schema_generator = SqliteSchemaGenerator

    def __init__(self, filename, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename
        self._transaction_class = type('TransactionWrapper', (TransactionWrapper, self.__class__), {})
        self._single_connection_class = type(
            'SingleConnectionWrapper',
            (SingleConnectionWrapper, self.__class__),
            {}
        )

    async def create_connection(self):
        pass

    async def close(self):
        pass

    def acquire_connection(self):
        connection = aiosqlite.connect(self.filename)
        return connection

    def in_transaction(self):
        return self._transaction_class(connection=aiosqlite.connect(self.filename))

    async def execute_query(self, query, get_inserted_id=False):
        self.log.debug(query)
        async with self.acquire_connection() as connection:
            connection._conn.row_factory = sqlite3.Row
            cursor = await connection.execute(query)
            await self._commit(connection)
            results = await cursor.fetchall()
            if get_inserted_id:
                await cursor.execute('SELECT last_insert_rowid()')
                inserted_id = await cursor.fetchone()
                return inserted_id
            return [dict(row) for row in results]

    async def execute_script(self, script):
        async with self.acquire_connection() as connection:
            self.log.debug(script)
            await connection.executescript(script)

    async def get_single_connection(self):
        connection = aiosqlite.connect(self.filename)
        connection.start()
        await connection._connect()
        return self._single_connection_class(connection, self)

    async def release_single_connection(self, single_connection):
        await single_connection.connection.close()

    async def _commit(self, connection):
        await connection.commit()


class TransactionWrapper(SqliteClient):
    def __init__(self, connection):
        self._connection = connection
        self.log = logging.getLogger('db_client')
        self.single_connection = True
        self._single_connection_class = type(
            'SingleConnectionWrapper',
            (SingleConnectionWrapper, self.__class__),
            {}
        )
        self._transaction_class = self.__class__

    def acquire_connection(self):
        return ConnectionWrapper(self._connection)

    async def get_single_connection(self):
        return self._single_connection_class(self._connection, self)

    async def release_single_connection(self, single_connection):
        pass

    async def start(self):
        self._connection.start()
        await self._connection._connect()

    async def rollback(self):
        await self._connection.rollback()
        await self._connection.close()

    async def commit(self):
        await self._connection.commit()
        await self._connection.close()

    async def __aenter__(self):
        self._connection.start()
        await self._connection._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self._connection.rollback()
            await self._connection.close()
            return False
        await self._connection.commit()
        await self._connection.close()

    async def _commit(self, connection):
        pass
