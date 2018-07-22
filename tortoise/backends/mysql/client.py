import logging
import re

import aiomysql
import pymysql

from tortoise.backends.base.client import (BaseDBAsyncClient, ConnectionWrapper,
                                           SingleConnectionWrapper)
from tortoise.backends.mysql.executor import MySQLExecutor
from tortoise.backends.mysql.schema_generator import MySQLSchemaGenerator
from tortoise.exceptions import ConfigurationError, IntegrityError, OperationalError


class MySQLClient(BaseDBAsyncClient):
    executor_class = MySQLExecutor
    schema_generator = MySQLSchemaGenerator

    def __init__(
            self,
            database,
            host='127.0.0.1',
            port=3306, user='root',
            password='',
            single_connection=False,
            *args,
            **kwargs):
        super().__init__(*args, **kwargs)

        self.host = host
        self.port = int(port)  # make sure port is int type
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

        self._transaction_class = type(
            'TransactionWrapper', (TransactionWrapper, self.__class__), {}
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
            **self.template
        )
        await self.execute_script(
            'CREATE DATABASE {}'.format(self.database)
        )
        self._connection.close()
        self.single_connection = single_connection

    async def db_delete(self):
        single_connection = self.single_connection
        self.single_connection = True
        self._connection = await aiomysql.connect(
            **self.template
        )
        try:
            await self.execute_script('DROP DATABASE {}'.format(self.database))
        except pymysql.err.DatabaseError:
            pass
        self._connection.close()
        self.single_connection = single_connection

    def acquire_connection(self):
        if not self.single_connection:
            return self._db_pool.acquire()
        else:
            return ConnectionWrapper(self._connection)

    def in_transaction(self):
        if self.single_connection:
            return self._transaction_class(connection=self._connection)
        else:
            return self._transaction_class(pool=self._db_pool)

    async def execute_query(self, query):
        mysql_query = query.replace('\"', '`')
        r = re.search(r'(.*)(\{.*\})(.*)', mysql_query)
        if r:
            mysql_query = r.group(1) \
                        + r.group(2).replace('`', '"') \
                        + r.group(3)
        try:
            async with self.acquire_connection() as connection:
                async with connection.cursor(aiomysql.DictCursor) as cursor:
                    self.log.debug(mysql_query)

                    affected_row = await cursor.execute(mysql_query)

                    if "SELECT" in query or "select" in query:
                        result = await cursor.fetchall()
                        return result

                    await connection.commit()
                    return affected_row

        except pymysql.err.OperationalError as exc:
            OperationalError(exc)
        except pymysql.err.ProgrammingError as exc:
            OperationalError(exc)
        except pymysql.err.IntegrityError as exc:
            IntegrityError(exc)

    async def execute_script(self, script):
        try:
            async with self.acquire_connection() as connection:
                async with connection.cursor() as cursor:
                    self.log.debug(script)
                    await cursor.execute(script)

        except pymysql.err.OperationalError as exc:
            OperationalError(exc)
        except pymysql.err.IntegrityError as exc:
            IntegrityError(exc)

    async def get_single_connection(self):
        if self.single_connection:
            return self._single_connection_class(self._connection, self)
        else:
            connection = await self._db_pool._acquire()
            return self._single_connection_class(connection, self)

    async def release_single_connection(self, single_connection):
        if not self.single_connection:
            await self._db_pool.release(single_connection.connection)


class TransactionWrapper(MySQLClient):
    def __init__(self, pool=None, connection=None):
        if pool and connection:
            raise ConfigurationError('You must pass either connection or pool')
        self._connection = connection
        self.log = logging.getLogger('db_client')
        self._pool = pool
        self.single_connection = True
        self._single_connection_class = type(
            'SingleConnectionWrapper', (SingleConnectionWrapper, self.__class__), {}
        )
        self._transaction_class = self.__class__

    def acquire_connection(self):
        return ConnectionWrapper(self._connection)

    async def _get_connection(self):
        return await self._pool._acquire()

    async def start(self):
        if not self._connection:
            self._connection = await self._get_connection()
        self.transaction = self._connection
        await self.transaction.begin()

    async def commit(self):
        await self.transaction.commit()
        if self._pool:
            await self._pool.release(self._connection)
            self._connection = None

    async def rollback(self):
        await self.transaction.rollback()
        if self._pool:
            await self._pool.release(self._connection)
            self._connection = None

    async def __aenter__(self):
        if not self._connection:
            self._connection = await self._get_connection()
        self.transaction = await self._connection.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.transaction.rollback()
            if self._pool:
                await self._pool.release(self._connection)
                self._connection = None
            return False
        if self._pool:
            await self._pool.release(self._connection)
            self._connection = None
