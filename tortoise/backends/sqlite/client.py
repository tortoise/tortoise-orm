import logging
import os
import sqlite3
from functools import wraps
from typing import List, Optional  # noqa

import aiosqlite

from tortoise.backends.base.client import (BaseDBAsyncClient, BaseTransactionWrapper,
                                           ConnectionWrapper)
from tortoise.backends.sqlite.executor import SqliteExecutor
from tortoise.backends.sqlite.schema_generator import SqliteSchemaGenerator
from tortoise.exceptions import IntegrityError, OperationalError, TransactionManagementError
from tortoise.transactions import current_transaction_map


def translate_exceptions(func):
    @wraps(func)
    async def wrapped(self, query, *args):
        try:
            return await func(self, query, *args)
        except sqlite3.OperationalError as exc:
            raise OperationalError(exc)
        except sqlite3.IntegrityError as exc:
            raise IntegrityError(exc)
    return wrapped


class SqliteClient(BaseDBAsyncClient):
    executor_class = SqliteExecutor
    schema_generator = SqliteSchemaGenerator

    def __init__(self, file_path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.filename = file_path
        self._transaction_class = type(
            'TransactionWrapper', (TransactionWrapper, self.__class__), {}
        )
        self._connection = None  # type: Optional[aiosqlite.Connection]

    async def create_connection(self) -> None:
        if not self._connection:  # pragma: no branch
            self._connection = aiosqlite.connect(self.filename, isolation_level=None)
            self._connection.start()
            await self._connection._connect()
            self._connection._conn.row_factory = sqlite3.Row

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def db_create(self) -> None:
        pass

    async def db_delete(self) -> None:
        await self.close()
        try:
            os.remove(self.filename)
        except FileNotFoundError:  # pragma: nocoverage
            pass

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self._connection)

    def _in_transaction(self) -> 'TransactionWrapper':
        return self._transaction_class(self.connection_name, connection=self._connection)

    @translate_exceptions
    async def execute_insert(self, query: str, values: list) -> int:
        self.log.debug('%s: %s', query, values)
        async with self.acquire_connection() as connection:
            return (await connection.execute_insert(query, values))[0]

    @translate_exceptions
    async def execute_query(self, query: str) -> List[dict]:
        self.log.debug(query)
        async with self.acquire_connection() as connection:
            return [dict(row) for row in await connection.execute_fetchall(query)]

    @translate_exceptions
    async def execute_script(self, query: str) -> None:
        self.log.debug(query)
        async with self.acquire_connection() as connection:
            await connection.executescript(query)

    async def get_single_connection(self) -> 'SqliteClient':
        return self

    async def release_single_connection(self, single_connection: BaseDBAsyncClient) -> None:
        pass


class TransactionWrapper(SqliteClient, BaseTransactionWrapper):
    def __init__(self, connection_name: str, connection: aiosqlite.Connection) -> None:
        self.connection_name = connection_name
        self._connection = connection  # type: aiosqlite.Connection
        self.log = logging.getLogger('db_client')
        self._transaction_class = self.__class__
        self._old_context_value = None
        self._finalized = False

    async def start(self) -> None:
        try:
            await self._connection.commit()
            await self._connection.execute('BEGIN')
        except sqlite3.OperationalError as exc:  # pragma: nocoverage
            raise TransactionManagementError(exc)
        current_transaction = current_transaction_map[self.connection_name]
        self._old_context_value = current_transaction.get()
        current_transaction.set(self)

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError('Transaction already finalised')
        self._finalized = True
        await self._connection.rollback()
        current_transaction_map[self.connection_name].set(self._old_context_value)

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError('Transaction already finalised')
        self._finalized = True
        await self._connection.commit()
        current_transaction_map[self.connection_name].set(self._old_context_value)
