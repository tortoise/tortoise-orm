from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from tortoise.contrib import test
from tortoise.contrib.fastapi import RegisterTortoise


@pytest.mark.asyncio
@test.requireCapability(dialect="sqlite")
@patch("tortoise.Tortoise.init")
@patch("tortoise.Tortoise.close_connections")
async def test_await(
    mocked_close_connections: AsyncMock,
    mocked_init: AsyncMock,
    db,
) -> None:
    app = FastAPI()
    orm = await RegisterTortoise(
        app,
        db_url="sqlite://:memory:",
        modules={"models": ["__main__"]},
    )
    mocked_init.assert_awaited_once()
    mocked_init.assert_called_once_with(
        config=None,
        config_file=None,
        db_url="sqlite://:memory:",
        modules={"models": ["__main__"]},
        use_tz=True,
        timezone="UTC",
        _create_db=False,
        _enable_global_fallback=True,
    )
    await orm.close_orm()
    mocked_close_connections.assert_awaited_once()


@pytest.mark.asyncio
@test.requireCapability(dialect="sqlite")
@patch("tortoise.Tortoise.init")
@patch("tortoise.Tortoise.close_connections")
async def test_await_use_tz_false(
    mocked_close_connections: AsyncMock,
    mocked_init: AsyncMock,
    db,
) -> None:
    app = FastAPI()
    orm = await RegisterTortoise(
        app,
        db_url="sqlite://:memory:",
        modules={"models": ["__main__"]},
        use_tz=False,
    )
    mocked_init.assert_awaited_once()
    mocked_init.assert_called_once_with(
        config=None,
        config_file=None,
        db_url="sqlite://:memory:",
        modules={"models": ["__main__"]},
        use_tz=False,
        timezone="UTC",
        _create_db=False,
        _enable_global_fallback=True,
    )
    await orm.close_orm()
    mocked_close_connections.assert_awaited_once()
