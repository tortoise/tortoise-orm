import asyncio
import re
from abc import ABCMeta
from typing import Any, Optional, Union

import aioodbc

from tortoise import BaseDBAsyncClient
from tortoise.backends.base.client import (
    BaseTransactionWrapper,
    ConnectionWrapper,
    NestedTransactionPooledContext,
    PoolConnectionWrapper,
    TransactionContext,
    TransactionContextPooled,
)
from tortoise.backends.odbc.executor import ODBCExecutor
from tortoise.exceptions import TransactionManagementError


class ODBCClient(BaseDBAsyncClient, metaclass=ABCMeta):
    executor_class = ODBCExecutor

    def __init__(
        self,
        dsn: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._kwargs = kwargs.copy()
        self._kwargs.pop("connection_name", None)
        self._kwargs.pop("fetch_inserted", None)

        self.dsn = dsn
        find = re.search(r"(?<=\bDatabase=).*?(?=;)", dsn)
        self.database = find.group(0) if find else None
        self.minsize = self._kwargs.pop("minsize", 1)
        self.maxsize = self._kwargs.pop("maxsize", 5)
        self.pool_recycle = self._kwargs.pop("pool_recycle", -1)
        self.echo = self._kwargs.pop("echo", False)

        self._pool: Optional[aioodbc.Pool] = None
        self._connection = None

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f"CREATE DATABASE {self.database}")
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f"DROP DATABASE {self.database}")
        await self.close()

    def _in_transaction(self) -> "TransactionContext":
        return TransactionContextPooled(TransactionWrapper(self))

    async def create_connection(self, with_db: bool) -> None:
        self._pool = await aioodbc.create_pool(
            dsn=self.dsn,
            minsize=self.minsize,
            maxsize=self.maxsize,
            pool_recycle=self.pool_recycle,
            echo=self.echo,
            **self._kwargs,
        )
        self.log.debug("Created connection %s pool with params: %s", self._pool, self._kwargs)

    async def close(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self.log.debug("Closed connection %s with params: %s", self._connection, self._kwargs)
            self._pool = None

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return PoolConnectionWrapper(self)


class TransactionWrapper(ODBCClient, BaseTransactionWrapper):
    def __init__(self, connection: ODBCClient) -> None:
        self.connection_name = connection.connection_name
        self._connection: aioodbc.Connection = connection._connection
        self._lock = asyncio.Lock()
        self._trxlock = asyncio.Lock()
        self.log = connection.log
        self._finalized: Optional[bool] = None
        self.fetch_inserted = connection.fetch_inserted
        self._parent = connection

    def _in_transaction(self) -> "TransactionContext":
        return NestedTransactionPooledContext(self)

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return PoolConnectionWrapper(self)

    async def execute_many(self, query: str, values: list) -> None:
        async with self.acquire_connection() as connection:
            self.log.debug("%s: %s", query, values)
            async with connection.cursor() as cursor:
                await cursor.executemany(query, values)

    async def start(self) -> None:
        self._finalized = False

    async def commit(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.commit()
        self._finalized = True

    async def rollback(self) -> None:
        if self._finalized:
            raise TransactionManagementError("Transaction already finalised")
        await self._connection.rollback()
        self._finalized = True
