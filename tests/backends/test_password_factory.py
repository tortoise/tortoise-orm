from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from tortoise import Tortoise
from tortoise.backends.base.client import resolve_password
from tortoise.context import TortoiseContext


@pytest.mark.asyncio
async def test_resolve_password_passes_through_plain_values():
    assert await resolve_password("foomip") == "foomip"
    assert await resolve_password(None) is None


@pytest.mark.asyncio
async def test_resolve_password_calls_sync_and_async_callables():
    calls = []

    def sync_factory() -> str:
        calls.append("sync")
        return "sync-token"

    async def async_factory() -> str:
        calls.append("async")
        return "async-token"

    assert await resolve_password(sync_factory) == "sync-token"
    assert await resolve_password(async_factory) == "async-token"
    assert calls == ["sync", "async"]


@pytest.mark.asyncio
async def test_asyncpg_forwards_password_callable_to_the_driver():
    """asyncpg resolves the callable itself, once per new connection."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        pytest.skip("asyncpg not installed")

    async def token() -> str:
        return "token"

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
                            "password": token,
                            "port": 5432,
                            "user": "root",
                        },
                    }
                },
                False,
            )
            await ctx.connections.get("models").create_connection(with_db=True)

            assert asyncpg_connect.await_args.kwargs["password"] is token


@pytest.mark.asyncio
async def test_psycopg_keeps_the_password_out_of_the_conninfo():
    try:
        import psycopg  # noqa: F401
    except ImportError:
        pytest.skip("psycopg not installed")

    def token() -> str:
        return "token"

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
                            "password": token,
                            "port": 5432,
                            "user": "root",
                            "timeout": 1,
                        },
                    }
                },
                False,
            )
            client = ctx.connections.get("models")
            await client.create_connection(with_db=True)

            assert "password" not in client._template["conninfo"]
            assert client._template["connection_class"].__name__ == "PasswordFactoryConnection"


@pytest.mark.asyncio
async def test_psycopg_connection_class_mints_a_password_per_connection():
    try:
        from tortoise.backends.psycopg.client import password_factory_connection_class
    except ImportError:
        pytest.skip("psycopg not installed")

    tokens = iter(["token-1", "token-2"])
    seen: list[dict[str, Any]] = []

    class RecordingConnection:
        @classmethod
        async def connect(cls, conninfo: str = "", **kwargs: Any) -> str:
            seen.append(kwargs)
            return "connection"

    async def token() -> str:
        return next(tokens)

    connection_class = password_factory_connection_class(RecordingConnection, token)  # type: ignore[arg-type]

    assert await connection_class.connect("host=127.0.0.1") == "connection"
    assert await connection_class.connect("host=127.0.0.1") == "connection"
    assert [kwargs["password"] for kwargs in seen] == ["token-1", "token-2"]


def test_star_password_ignores_password_callables():
    def factory() -> str:
        return "s3cret"  # pragma: nocoverage

    config = {
        "models": {"engine": "tortoise.backends.asyncpg", "credentials": {"password": factory}}
    }

    # Must not raise: masking only applies to string passwords
    assert "s3cret" not in Tortoise.star_password(config)
