import logging
from typing import Sequence

from pypika import Query

from tortoise.backends.base.executor import BaseExecutor
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class BaseDBAsyncClient:
    query_class = Query
    executor_class = BaseExecutor
    schema_generator = BaseSchemaGenerator

    def __init__(self, connection_name: str, single_connection: bool = True, **kwargs) -> None:
        self.log = logging.getLogger('db_client')
        self.single_connection = single_connection
        self.connection_name = connection_name
        self._single_connection_class = type(
            'SingleConnectionWrapper', (SingleConnectionWrapper, self.__class__), {}
        )

    async def create_connection(self) -> None:
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

    async def get_single_connection(self) -> 'BaseDBAsyncClient':
        raise NotImplementedError()  # pragma: nocoverage

    async def release_single_connection(self, single_connection: 'BaseDBAsyncClient') -> None:
        raise NotImplementedError()  # pragma: nocoverage


class ConnectionWrapper:
    __slots__ = ('connection', )

    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class SingleConnectionWrapper(BaseDBAsyncClient):
    # pylint: disable=W0223,W0231

    def __init__(self, connection_name: str, connection, closing_callback=None) -> None:
        self.log = logging.getLogger('db_client')
        self.connection_name = connection_name
        self.connection = connection
        self.single_connection = True
        self.closing_callback = closing_callback

    def acquire_connection(self) -> ConnectionWrapper:
        return ConnectionWrapper(self.connection)

    async def get_single_connection(self) -> 'SingleConnectionWrapper':
        # Real class object is generated in runtime, so we use __class__ reference
        # instead of using SingleConnectionWrapper directly
        return self.__class__(self.connection_name, self.connection, self)

    async def release_single_connection(self, single_connection: 'BaseDBAsyncClient') -> None:
        return

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.closing_callback:
            await self.closing_callback(self)


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

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
