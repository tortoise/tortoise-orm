import logging
from copy import deepcopy
from typing import Sequence

from pypika import Query

from tortoise.backends.base.executor import BaseExecutor
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class Capabilities:
    def __init__(
        self, dialect: str, *, connection: dict, safe_indexes: bool = False
    ) -> None:
        super().__setattr__('_mutable', True)

        self.dialect = dialect
        self.connection = deepcopy(connection)
        self.safe_indexes = safe_indexes

        super().__setattr__('_mutable', False)

    def __setattr__(self, attr, value):
        if not getattr(self, '_mutable', False):
            raise AttributeError(attr)
        return super().__setattr__(attr, value)

    def __str__(self) -> str:
        return str(self.__dict__)


class BaseDBAsyncClient:
    query_class = Query
    executor_class = BaseExecutor
    schema_generator = BaseSchemaGenerator

    def __init__(self, connection_name: str, **kwargs) -> None:
        self.log = logging.getLogger('db_client')
        self.connection_name = connection_name
        self.capabilities = Capabilities('', connection={})

    async def create_connection(self, with_db: bool) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def close(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def db_create(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def db_delete(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    def acquire_connection(self) -> 'ConnectionWrapper':
        raise NotImplementedError()  # pragma: nocoverage

    def _in_transaction(self) -> 'BaseTransactionWrapper':
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_insert(self, query: str, values: list) -> int:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_query(self, query: str) -> Sequence[dict]:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_script(self, query: str) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_explain(self, query: str) -> Sequence[dict]:
        raise NotImplementedError()  # pragma: nocoverage


class ConnectionWrapper:
    __slots__ = ('connection', )

    def __init__(self, connection) -> None:
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


class BaseTransactionWrapper:
    async def start(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def rollback(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def commit(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
