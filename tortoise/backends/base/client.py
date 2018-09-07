import logging

from pypika import Query

from tortoise.backends.base.executor import BaseExecutor
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class BaseDBAsyncClient:
    query_class = Query
    executor_class = BaseExecutor
    schema_generator = BaseSchemaGenerator

    def __init__(self, connection_name, single_connection=True, **kwargs):
        self.log = logging.getLogger('db_client')
        self.single_connection = single_connection
        self.connection_name = connection_name
        self._single_connection_class = type(
            'SingleConnectionWrapper', (SingleConnectionWrapper, self.__class__), {}
        )

    async def create_connection(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def close(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def db_create(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def db_delete(self):
        raise NotImplementedError()  # pragma: nocoverage

    def acquire_connection(self):
        raise NotImplementedError()  # pragma: nocoverage

    def _in_transaction(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_query(self, query):
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_script(self, script):
        raise NotImplementedError()  # pragma: nocoverage

    async def get_single_connection(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def release_single_connection(self, single_connection):
        raise NotImplementedError()  # pragma: nocoverage


class ConnectionWrapper:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class SingleConnectionWrapper(BaseDBAsyncClient):
    def __init__(self, connection_name, connection, closing_callback=None):
        self.connection_name = connection_name
        self.connection = connection
        self.log = logging.getLogger('db_client')
        self.single_connection = True
        self.closing_callback = closing_callback

    def acquire_connection(self):
        return ConnectionWrapper(self.connection)

    async def get_single_connection(self):
        # Real class object is generated in runtime, so we use __class__ reference
        # instead of using SingleConnectionWrapper directly
        return self.__class__(self.connection_name, self.connection, self)

    async def release_single_connection(self, single_connection):
        return

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.closing_callback:
            await self.closing_callback(self)


class BaseTransactionWrapper:
    async def start(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def rollback(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def commit(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def __aenter__(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError()  # pragma: nocoverage
