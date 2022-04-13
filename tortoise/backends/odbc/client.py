from abc import ABC
from typing import Any, Optional, Union

import asyncodbc
import pyodbc

from tortoise import BaseDBAsyncClient
from tortoise.backends.base.client import ConnectionWrapper, PoolConnectionWrapper
from tortoise.backends.odbc.executor import ODBCExecutor
from tortoise.exceptions import DBConnectionError


class ODBCClient(BaseDBAsyncClient, ABC):
    executor_class = ODBCExecutor

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._kwargs = kwargs.copy()
        self._kwargs.pop("connection_name", None)
        self._kwargs.pop("fetch_inserted", None)

        self.database = self._kwargs.pop("database", None)
        self.minsize = self._kwargs.pop("minsize", 1)
        self.maxsize = self._kwargs.pop("maxsize", 10)
        self.pool_recycle = self._kwargs.pop("pool_recycle", -1)
        self.echo = self._kwargs.pop("echo", False)
        self.dsn: Optional[str] = None

        self._template: dict = {}
        self._pool: Optional[asyncodbc.Pool] = None
        self._connection = None

    async def db_create(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f"CREATE DATABASE {self.database}")
        await self.close()

    async def db_delete(self) -> None:
        await self.create_connection(with_db=False)
        await self.execute_script(f"DROP DATABASE {self.database}")
        await self.close()

    async def create_connection(self, with_db: bool) -> None:
        self._template = {
            "minsize": self.minsize,
            "maxsize": self.maxsize,
            "echo": self.echo,
            "pool_recycle": self.pool_recycle,
            "dsn": self.dsn,
            **self._kwargs,
        }
        if with_db:
            self._template["database"] = self.database
        try:
            self._pool = await asyncodbc.create_pool(
                **self._template,
            )
            self.log.debug("Created connection %s pool with params: %s", self._pool, self._template)
        except pyodbc.InterfaceError:
            raise DBConnectionError(f"Can't establish connection to database {self.database}")

    async def close(self) -> None:
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self.log.debug("Closed connection %s with params: %s", self._connection, self._template)
            self._pool = None

    def acquire_connection(self) -> Union["ConnectionWrapper", "PoolConnectionWrapper"]:
        return PoolConnectionWrapper(self)
