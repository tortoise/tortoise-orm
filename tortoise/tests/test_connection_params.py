from asynctest.mock import CoroutineMock, patch

from tortoise import Tortoise
from tortoise.contrib import test


class TestConnectionParams(test.TestCase):
    async def test_mysql_connection_params(self):
        with patch("aiomysql.connect", new=CoroutineMock()) as mysql_connect:
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
                            "charset": "utf-8",
                        },
                    }
                },
                False,
            )

            mysql_connect.assert_awaited_once_with(  # nosec
                autocommit=True,
                charset="utf-8",
                connect_timeout=1.5,
                db="test",
                host="127.0.0.1",
                password="foomip",
                port=3306,
                user="root",
            )

    async def test_postres_connection_params(self):
        try:
            with patch("asyncpg.connect", new=CoroutineMock()) as asyncpg_connect:
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
                )
        except ImportError:
            self.skipTest("asyncpg not installed")
