from unittest.mock import AsyncMock, patch

import asyncpg
import pytest

from tortoise.context import TortoiseContext


@pytest.mark.asyncio
async def test_mysql_connection_params():
    with patch(
        "tortoise.backends.mysql.client.mysql.create_pool", new=AsyncMock()
    ) as mysql_connect:
        ctx = TortoiseContext()
        async with ctx:
            await ctx.connections._init(
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
            await ctx.connections.get("models").create_connection(with_db=True)

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


@pytest.mark.asyncio
async def test_asyncpg_connection_params():
    try:
        with patch(
            "tortoise.backends.asyncpg.client.asyncpg.create_pool", new=AsyncMock()
        ) as asyncpg_connect:
            ctx = TortoiseContext()
            async with ctx:
                await ctx.connections._init(
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
                await ctx.connections.get("models").create_connection(with_db=True)

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
        pytest.skip("asyncpg not installed")


@pytest.mark.asyncio
async def test_psycopg_connection_params():
    try:
        with patch(
            "tortoise.backends.psycopg.client.PsycopgClient.create_pool", new=AsyncMock()
        ) as patched_create_pool:
            mocked_pool = AsyncMock()
            patched_create_pool.return_value = mocked_pool
            ctx = TortoiseContext()
            async with ctx:
                await ctx.connections._init(
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
                await ctx.connections.get("models").create_connection(with_db=True)

                patched_create_pool.assert_awaited_once()
                mocked_pool.open.assert_awaited_once_with(  # nosec
                    wait=True,
                    timeout=1,
                )
    except ImportError:
        pytest.skip("psycopg not installed")
