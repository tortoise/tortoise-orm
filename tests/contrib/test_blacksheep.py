from unittest.mock import AsyncMock, patch

import pytest
from blacksheep.server import Application

from tortoise.contrib.blacksheep import register_tortoise


@pytest.mark.asyncio
async def test_register_tortoise_enables_global_fallback() -> None:
    with (
        patch("tortoise.contrib.blacksheep.Tortoise") as mocked_tortoise,
        patch("tortoise.contrib.blacksheep.get_connections"),
    ):
        mocked_tortoise.init = AsyncMock()
        mocked_tortoise.close_connections = AsyncMock()
        app = Application()
        register_tortoise(
            app,
            db_url="sqlite://:memory:",
            modules={"models": ["__main__"]},
        )

        await app.start()
        mocked_tortoise.init.assert_awaited_once_with(
            config=None,
            config_file=None,
            db_url="sqlite://:memory:",
            modules={"models": ["__main__"]},
            _enable_global_fallback=True,
        )

        await app.stop()
        mocked_tortoise.close_connections.assert_awaited_once()
