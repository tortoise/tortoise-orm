import logging

import aiomysql

from tortoise.backends.mysql.executor import MySQLExecutor
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.backends.base.client import (BaseDBAsyncClient, ConnectionWrapper,
                                           SingleConnectionWrapper)


class MySQLAsyncClient(BaseDBAsyncClient):
    executor_class = MySQLExecutor
    schema_generator = MySQLSchemaGenerator

    def __init__(self, database, host='127.0.0.1', port=3306, user='root', password='', single_connection=False, *args, **kwargs):
        super().__init__(*argsm **kwargs)

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self.template = {'host': self.host, 
                         'port': self.port, 
                         'user': self.user, 
                         'password': self.password, 
                         'database': self.databse}

        self.log = logging.getLogger('db_client')
        self.single_connection = single_connection
        self._single_connection_class = type(
            'SingleConnectionWrapper', (SingleConnectionWrapper, self.__class__), {}
        )

        self._single_conneciton = None
        self._connection = None

    async def create_connection(self):
        self._connection = await aiomysql.connect(self.template)
        
        self.log.debug(
            'Created connection with params: '
            'user={user} database={database} host={host} port={port}'.format(
                user=self.user, database=self.database, host=self.host, port=self.port
                )
            )
        
    async def close(self):
        await self._connection.close()

    async def db_create(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def db_delete(self):
        raise NotImplementedError()  # pragma: nocoverage

    def acquire_connection(self):
        raise NotImplementedError()  # pragma: nocoverage

    def in_transaction(self):
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
