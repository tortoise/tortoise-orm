import os
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

try:
    import asyncmy as mysql
except ImportError:
    import aiomysql as mysql

from tortoise import timezone
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


@pytest.mark.asyncio
async def test_mysql_session_timezone_uses_configured_tz():
    """Test that MySQL session timezone reflects the configured timezone, not UTC.

    Regression test for https://github.com/tortoise/tortoise-orm/issues/2114
    """
    mock_cursor = AsyncMock()

    # connection.cursor() must return a sync object that supports async-with
    cursor_cm = MagicMock()
    cursor_cm.__aenter__ = AsyncMock(return_value=mock_cursor)
    cursor_cm.__aexit__ = AsyncMock(return_value=False)

    mock_connection = MagicMock()
    mock_connection.cursor.return_value = cursor_cm

    mock_pool = MagicMock(spec=mysql.Pool)
    mock_pool.acquire = AsyncMock(return_value=mock_connection)
    mock_pool.release = AsyncMock()

    old_use_tz = os.environ.get("USE_TZ")
    old_tz = os.environ.get("TIMEZONE")
    try:
        os.environ["USE_TZ"] = "True"
        os.environ["TIMEZONE"] = "Asia/Shanghai"
        timezone._reset_timezone_cache()

        with patch(
            "tortoise.backends.mysql.client.mysql.create_pool",
            new=AsyncMock(return_value=mock_pool),
        ):
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
                            },
                        }
                    },
                    False,
                )
                await ctx.connections.get("models").create_connection(with_db=True)

                # Verify SET time_zone was called with Asia/Shanghai offset (+8:00)
                tz_calls = [
                    call for call in mock_cursor.execute.await_args_list if "time_zone" in str(call)
                ]
                assert len(tz_calls) == 1, f"Expected 1 SET time_zone call, got {tz_calls}"
                assert "+8:00" in str(tz_calls[0]), (
                    f"Expected +8:00 for Asia/Shanghai, got {tz_calls[0]}"
                )
    finally:
        if old_use_tz is not None:
            os.environ["USE_TZ"] = old_use_tz
        else:
            os.environ.pop("USE_TZ", None)
        if old_tz is not None:
            os.environ["TIMEZONE"] = old_tz
        else:
            os.environ.pop("TIMEZONE", None)
        timezone._reset_timezone_cache()
