import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    import asyncmy as mysql
except ImportError:
    import aiomysql as mysql

from tortoise import timezone
from tortoise.backends.base.config_generator import expand_db_url
from tortoise.context import TortoiseContext


@asynccontextmanager
async def _mock_mysql_context() -> AsyncGenerator[tuple[AsyncMock, TortoiseContext], None]:
    pool = MagicMock()
    pool.wait_closed = AsyncMock()
    with patch(
        "tortoise.backends.mysql.client.mysql.create_pool", new=AsyncMock(return_value=pool)
    ) as mysql_connect:
        async with TortoiseContext() as ctx:
            yield mysql_connect, ctx


@pytest.mark.asyncio
async def test_mysql_connection_params():
    async with _mock_mysql_context() as (mysql_connect, ctx):
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
@pytest.mark.parametrize(
    "query,expected", [("sql_mode=", "''"), ("sql_mode=%27%27", "''"), ("sql_mode=ANSI", "ANSI")]
)
async def test_mysql_url_sql_mode(query, expected):
    async with _mock_mysql_context() as (mysql_connect, ctx):
        await ctx.connections._init(
            {"models": f"mysql://root:foomip@127.0.0.1:3306/test?{query}"}, False
        )
        await ctx.connections.get("models").create_connection(with_db=True)

        mysql_connect.assert_awaited_once()
        assert mysql_connect.await_args is not None
        assert mysql_connect.await_args.kwargs["sql_mode"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("pragma,expected", [("journal_mode", "wal"), ("foreign_keys", 1)])
async def test_sqlite_blank_string_option_keeps_default(tmp_path, pragma, expected):
    async with TortoiseContext() as ctx:
        await ctx.connections._init({"models": f"sqlite://{tmp_path}/test.sqlite?{pragma}="}, False)
        rows = await ctx.connections.get("models").execute_query_dict(f"PRAGMA {pragma}")
        assert rows[0][pragma] == expected


@pytest.mark.asyncio
async def test_asyncpg_connection_params():
    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")

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
async def test_psycopg_pool_checks_connection_health_on_checkout():
    """The pool must validate connections on checkout, or a connection dropped by the
    network while idle (e.g. a firewall/LB closing it silently) is handed straight to a
    caller and fails with ``psycopg.OperationalError: the connection is closed`` instead of
    being transparently replaced.

    Regression test for https://github.com/tortoise/tortoise-orm/issues/2007
    """
    try:
        from psycopg_pool import AsyncConnectionPool

        with patch(
            "tortoise.backends.psycopg.client.PsycopgClient.create_pool", new=AsyncMock()
        ) as patched_create_pool:
            patched_create_pool.return_value = AsyncMock()
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
                            },
                        }
                    },
                    False,
                )
                await ctx.connections.get("models").create_connection(with_db=True)

                patched_create_pool.assert_awaited_once()
                assert patched_create_pool.await_args is not None
                assert (
                    patched_create_pool.await_args.kwargs["check"]
                    is AsyncConnectionPool.check_connection
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


@pytest.mark.asyncio
async def test_asyncpg_multi_host_db_url():
    db_url = "postgres://u:p@h1:5433,h2/test?target_session_attrs=read-write"
    with patch(
        "tortoise.backends.asyncpg.client.asyncpg.create_pool", new=AsyncMock()
    ) as asyncpg_connect:
        ctx = TortoiseContext()
        async with ctx:
            await ctx.connections._init({"models": expand_db_url(db_url)}, False)
            await ctx.connections.get("models").create_connection(with_db=True)

            assert asyncpg_connect.await_args is not None
            kwargs = asyncpg_connect.await_args.kwargs
            assert kwargs["host"] == ["h1", "h2"]
            assert kwargs["port"] == [5433, 5432]
            assert kwargs["target_session_attrs"] == "read-write"


@pytest.mark.asyncio
async def test_psycopg_multi_host_db_url():
    try:
        from tortoise.backends.psycopg.client import PsycopgClient
    except ImportError:
        pytest.skip("psycopg not installed")

    db_url = "psycopg://u:p@h1:5433,h2/test?target_session_attrs=read-write"
    credentials = expand_db_url(db_url)["credentials"]
    client = PsycopgClient(connection_name="models", **credentials)
    with (
        patch.object(PsycopgClient, "create_pool", new=AsyncMock()) as create_pool,
        patch.object(PsycopgClient, "_post_connect", new=AsyncMock()),
    ):
        await client.create_connection(with_db=True)

    assert create_pool.await_args is not None
    conninfo = create_pool.await_args.kwargs["conninfo"]
    assert "host=h1,h2" in conninfo
    assert "port=5433,5432" in conninfo
    assert "target_session_attrs=read-write" in conninfo
    assert create_pool.await_args is not None
    assert "target_session_attrs" not in create_pool.await_args.kwargs


@pytest.mark.asyncio
async def test_psycopg_target_session_attrs_in_server_settings():
    try:
        from tortoise.backends.psycopg.client import PsycopgClient
    except ImportError:
        pytest.skip("psycopg not installed")

    client = PsycopgClient(
        connection_name="models",
        host="h1",
        server_settings={"target_session_attrs": "primary"},
    )
    with (
        patch.object(PsycopgClient, "create_pool", new=AsyncMock()) as create_pool,
        patch.object(PsycopgClient, "_post_connect", new=AsyncMock()),
    ):
        await client.create_connection(with_db=True)

    assert create_pool.await_args is not None
    assert "target_session_attrs=primary" in create_pool.await_args.kwargs["conninfo"]


def test_postgres_client_keeps_single_host_types() -> None:
    try:
        from tortoise.backends.asyncpg.client import AsyncpgDBClient
    except ImportError:
        pytest.skip("asyncpg not installed")

    client = AsyncpgDBClient(connection_name="models", host="h1", port="5433")  # type:ignore
    assert (client.host, client.port) == ("h1", 5433)
    client = AsyncpgDBClient(connection_name="models", host=("h1", "h2"), port=(5433, "5434"))  # type:ignore
    assert (client.host, client.port) == (["h1", "h2"], [5433, 5434])
