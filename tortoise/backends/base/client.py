import logging

from pypika import Query

from tortoise.backends.base.executor import BaseExecutor
from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class BaseDBAsyncClient:
    query_class = Query
    executor_class = BaseExecutor
    schema_generator = BaseSchemaGenerator

    def __init__(self, single_connection=False, *args, **kwargs):
        self.log = logging.getLogger('db_client')
        self.single_connection = single_connection
        self._single_connection_class = type(
            'SingleConnectionWrapper',
            (SingleConnectionWrapper, self.__class__),
            {}
        )

    async def create_connection(self):
        raise NotImplementedError()

    async def close(self):
        raise NotImplementedError()

    def acquire_connection(self):
        raise NotImplementedError()

    def in_transaction(self):
        raise NotImplementedError()

    async def execute_query(self, query):
        raise NotImplementedError()

    async def execute_script(self, script):
        raise NotImplementedError()

    async def get_single_connection(self):
        raise NotImplementedError()

    async def release_single_connection(self, single_connection):
        raise NotImplementedError()


class ConnectionWrapper:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class SingleConnectionWrapper(BaseDBAsyncClient):
    def __init__(self, connection, parent):
        self.connection = connection
        self.parent = parent
        self.log = logging.getLogger('db_client')
        self.single_connection = True

    def acquire_connection(self):
        return ConnectionWrapper(self.connection)

    async def get_single_connection(self):
        # Real class object is generated in runtime, so we use __class__ reference
        # instead of using SingleConnectionWrapper directly
        return self.__class__(self.connection, self)

    async def release_single_connection(self, single_connection):
        return

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
