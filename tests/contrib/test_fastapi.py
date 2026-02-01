from unittest.mock import AsyncMock, patch

from fastapi import FastAPI

from tortoise.contrib import test
from tortoise.contrib.fastapi import RegisterTortoise


class TestRegisterTortoise(test.TestCase):
    @test.requireCapability(dialect="sqlite")
    @patch("tortoise.Tortoise.init")
    @patch("tortoise.connections.close_all")
    async def test_await(
        self,
        mocked_close: AsyncMock,
        mocked_init: AsyncMock,
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
            use_tz=False,
            timezone="UTC",
            _create_db=False,
        )
        await orm.close_orm()
        mocked_close.assert_awaited_once()
