import logging
import os
import sqlite3

import aiosqlite

from tortoise.backends.base.client import (BaseDBAsyncClient, BaseTransactionWrapper,
                                           ConnectionWrapper)
from tortoise.backends.sqlite.executor import SqliteExecutor
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator
from tortoise.exceptions import IntegrityError, OperationalError, TransactionManagementError
from tortoise.transactions import current_transaction_map


class SqliteClient(BaseDBAsyncClient):
    executor_class = SqliteExecutor
    schema_generator = SqliteSchemaGenerator

    def __init__(self, file_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = file_path
        self._transaction_class = type(
            'TransactionWrapper', (TransactionWrapper, self.__class__), {}
        )
        self._connection = None

    async def create_connection(self):
        if not self._connection:  # pragma: no branch
            self._connection = aiosqlite.connect(self.filename, isolation_level=None)
            self._connection.start()
            await self._connection._connect()

    async def close(self):
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def db_create(self):
        pass

    async def db_delete(self):
        await self.close()
        try:
            os.remove(self.filename)
        except FileNotFoundError:  # pragma: nocoverage
            pass

    def acquire_connection(self):
        return ConnectionWrapper(self._connection)

    def _in_transaction(self):
        return self._transaction_class(self.connection_name, connection=self._connection)

    async def execute_query(self, query, get_inserted_id=False):
        self.log.debug(query)
        try:
            async with self.acquire_connection() as connection:
                connection._conn.row_factory = sqlite3.Row
                cursor = await connection.execute(query)
                results = await cursor.fetchall()
                if get_inserted_id:
                    await cursor.execute('SELECT last_insert_rowid()')
                    inserted_id = await cursor.fetchone()
                    return inserted_id
                return [dict(row) for row in results]
        except sqlite3.OperationalError as exc:
            raise OperationalError(exc)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(exc)

    async def execute_script(self, script):
        connection = self._connection
        self.log.debug(script)
        try:
            await connection.executescript(script)
        except sqlite3.OperationalError as exc:
            raise OperationalError(exc)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(exc)

    async def get_single_connection(self):
        return self

    async def release_single_connection(self, single_connection):
        pass


class TransactionWrapper(SqliteClient, BaseTransactionWrapper):
    def __init__(self, connection_name, connection):
        self.connection_name = connection_name
        self._connection = connection
        self.log = logging.getLogger('db_client')
        self._transaction_class = self.__class__
        self._old_context_value = None
        self._finalized = False

    async def start(self):
        try:
            await self._connection.commit()
            await self._connection.execute('BEGIN')
        except sqlite3.OperationalError as exc:  # pragma: nocoverage
            raise TransactionManagementError(exc)
        current_transaction = current_transaction_map[self.connection_name]
        self._old_context_value = current_transaction.get()
        current_transaction.set(self)

    async def rollback(self):
        if self._finalized:
            raise TransactionManagementError('Transaction already finalised')
        self._finalized = True
        await self._connection.rollback()
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def commit(self):
        if self._finalized:
            raise TransactionManagementError('Transaction already finalised')
        self._finalized = True
        await self._connection.commit()
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
