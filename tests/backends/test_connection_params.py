from unittest.mock import AsyncMock, Mock, patch

import asyncpg
from psycopg import rows

from tortoise import Tortoise
from tortoise.backends.psycopg import client as psycopg_client
from tortoise.contrib import test


class TestConnectionParams(test.TestCase):
    async def asyncSetUp(self) -> None:
        pass

    async def asyncTearDown(self) -> None:
        pass

    async def test_mysql_connection_params(self):
        with patch("asyncmy.create_pool", new=AsyncMock()) as mysql_connect:
            await Tortoise._init_connections(
                {
                    "models": {
                        "engine": "tortoise.backends.mysql",
                        "credentials": {
                            "database": "test",
                            "host": "127.0.0.1",
                            "password": "foomip",
                            "port": 3306,
                            "user": "root",
                            "connect_timeout": 1.5,
                            "charset": "utf8mb4",
                        },
                    }
                },
                False,
            )

            mysql_connect.assert_awaited_once_with(  # nosec
                autocommit=True,
                charset="utf8mb4",
                connect_timeout=1.5,
                db="test",
                host="127.0.0.1",
                password="foomip",
                port=3306,
                user="root",
                maxsize=5,
                minsize=1,
                sql_mode="STRICT_TRANS_TABLES",
            )

    async def test_asyncpg_connection_params(self):
        try:
            with patch("asyncpg.create_pool", new=AsyncMock()) as asyncpg_connect:
                await Tortoise._init_connections(
                    {
                        "models": {
                            "engine": "tortoise.backends.asyncpg",
                            "credentials": {
                                "database": "test",
                                "host": "127.0.0.1",
                                "password": "foomip",
                                "port": 5432,
                                "user": "root",
                                "timeout": 30,
                                "ssl": True,
                            },
                        }
                    },
                    False,
                )

                asyncpg_connect.assert_awaited_once_with(  # nosec
                    None,
                    database="test",
                    host="127.0.0.1",
                    password="foomip",
                    port=5432,
                    ssl=True,
                    timeout=30,
                    user="root",
                    max_size=5,
                    min_size=1,
                    connection_class=asyncpg.connection.Connection,
                    loop=None,
                    server_settings={},
                )
        except ImportError:
            self.skipTest("asyncpg not installed")

    async def test_psycopg_connection_params(self):
        try:
            with patch("psycopg_pool.AsyncConnectionPool.open", new=AsyncMock()) as psycopg_connect:
                await Tortoise._init_connections(
                    {
                        "models": {
                            "engine": "tortoise.backends.psycopg",
                            "credentials": {
                                "database": "test",
                                "host": "127.0.0.1",
                                "password": "foomip",
                                "port": 5432,
                                "user": "root",
                                "timeout": 1,
                                "ssl": True,
                            },
                        }
                    },
                    False,
                )

                psycopg_connect.assert_awaited_once_with(  # nosec
                    wait=True,
                    timeout=1,
                )
        except ImportError:
            self.skipTest("psycopg not installed")
