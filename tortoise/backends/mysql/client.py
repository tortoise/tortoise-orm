import logging

import aiomysql

from tortoise.backends.mysql.executor import MySQLExecutor
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.backends.base.client import (BaseDBAsyncClient, ConnectionWrapper,
                                           SingleConnectionWrapper)


class MySQLClient(BaseDBAsyncClient):
    executor_class = MySQLExecutor
    schema_generator = MySQLSchemaGenerator

    def __init__(self, database, host='127.0.0.1', port=3306, user='root', password='', single_connection=False, *args, **kwargs):
        super().__init__(*argsm **kwargs)

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self.template = {
            'host': self.host, 
            'port': self.port, 
            'user': self.user, 
            'password': self.password, 
            'database': self.databse
        }

        self.log = logging.getLogger('db_client')
        self.single_connection = single_connection
        self._single_connection_class = type(
            'SingleConnectionWrapper', (SingleConnectionWrapper, self.__class__), {}
        )

        self._db_pool = None
        self._connection = None

    async def create_connection(self):
        if not self.single_connection:
            self._db_pool = await aiomysql.create_pool(self.template)
        else:
            self._connection = await aiomysql.connect(self.template)
        
        self.log.debug(
            'Created connection with params: '
            'user={user} database={database} host={host} port={port}'.format(
                user=self.user, database=self.database, host=self.host, port=self.port
                )
            )
        
    async def close(self):
        if not self.single_connection:
            await self._db_pool.wait_closed()
        else:
            self._connection.close()

    async def db_create(self):
        single_connection = self.single_connection
        self.single_connection = True
        self._connection = await aiomysql.connect(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=''
        )
        await self.execute_script(
            'CREATE DATABASE {} OWNER {}'.format(self.database, self.user)
        )
        self._connection.close()
        self.single_connection = single_connection

    async def db_delete(self):
        raise NotImplementedError()  # pragma: nocoverage

    def acquire_connection(self):
        if not self.single_connection:
            return self._db_pool.acquire()
        else:
            return ConnectionWrapper(self._connection)

    def in_transaction(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_query(self, query):
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_script(self, script):
        async with self.acquire_connection() as connection:
            self.log.debug(script)
            await connection.execute(script)

    async def get_single_connection(self):
        raise NotImplementedError()  # pragma: nocoverage

    async def release_single_connection(self, single_connection):
        raise NotImplementedError()  # pragma: nocoverage
