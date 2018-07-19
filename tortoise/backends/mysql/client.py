import logging

import aiomysql

from tortoise.backends.mysql.executor import MySQLExecutor
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.backends.base.client import (BaseDBAsyncClient, ConnectionWrapper,
                                           SingleConnectionWrapper)

from tortoise.exceptions import IntegrityError, OperationalError

class MySQLClient(BaseDBAsyncClient):
    executor_class = MySQLExecutor
    schema_generator = MySQLSchemaGenerator

    def __init__(self, database, host='127.0.0.1', port=3306, user='root', password='', single_connection=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
            self._db_pool = await aiomysql.create_pool(db=self.database, **self.template)
        else:
            self._connection = await aiomysql.connect(db=self.database, **self.template)
        
        self.log.debug(
            'Created connection with params: '
            'user={user} database={database} host={host} port={port}'.format(
                user=self.user, database=self.database, host=self.host, port=self.port
                )
            )
        
    async def close(self):
        if not self.single_connection:
            self._db_pool.close()
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
        mysql_query = query.replace("\"", "`")

        async with self.acquire_connection() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                self.log.debug(mysql_query)
                
                affected_row = await cursor.execute(mysql_query) 

                if "SELECT"  in mysql_query or "select" in mysql_query:
                    result = await cursor.fetchall()
                    return result 

                await connection.commit()
                return affected_row

    async def execute_script(self, script):
        async with self.acquire_connection() as connection:
            async with connection.cursor() as cursor: 
                self.log.debug(script)
                await cursor.execute(script)

    async def get_single_connection(self):
        if self.single_connection:
            return self._single_connection_class(self._connection, self)
        else:
            connection = await self._db_pool._acquire()
            return self._single_connection_class(connection, self)

    async def release_single_connection(self, single_connection):
        if not self.single_connection:
            await self._db_pool.release(single_connection.connection)
