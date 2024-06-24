import subprocess  # nosec
from unittest.mock import AsyncMock, patch

from tortoise.contrib import test
from tortoise.contrib.test import init_memory_sqlite


class TestDecorator(test.TestCase):
    @test.requireCapability(dialect="sqlite")
    async def test_script_with_init_memory_sqlite(self) -> None:
        r = subprocess.run(["python", "examples/basic.py"], capture_output=True)  # nosec
        output = r.stdout.decode()
        s = "[{'id': 1, 'name': 'Updated name'}, {'id': 2, 'name': 'Test 2'}]"
        self.assertIn(s, output)

    @test.requireCapability(dialect="sqlite")
    @patch("tortoise.Tortoise.init")
    @patch("tortoise.Tortoise.generate_schemas")
    async def test_init_memory_sqlite(
        self,
        mocked_generate: AsyncMock,
        mocked_init: AsyncMock,
    ) -> None:
        @init_memory_sqlite
        async def run():
            return "foo"

        res = await run()
        self.assertEqual(res, "foo")
        mocked_init.assert_awaited_once()
        mocked_init.assert_called_once_with(
            db_url="sqlite://:memory:", modules={"models": ["__main__"]}
        )
        mocked_generate.assert_awaited_once()

    @test.requireCapability(dialect="sqlite")
    @patch("tortoise.Tortoise.init")
    @patch("tortoise.Tortoise.generate_schemas")
    async def test_init_memory_sqlite_with_models(
        self,
        mocked_generate: AsyncMock,
        mocked_init: AsyncMock,
    ) -> None:
        @init_memory_sqlite(["app.models"])
        async def run():
            return "foo"

        res = await run()
        self.assertEqual(res, "foo")
        mocked_init.assert_awaited_once()
        mocked_init.assert_called_once_with(
            db_url="sqlite://:memory:", modules={"models": ["app.models"]}
        )
        mocked_generate.assert_awaited_once()

    @test.requireCapability(dialect="sqlite")
    @patch("tortoise.Tortoise.init")
    @patch("tortoise.Tortoise.generate_schemas")
    async def test_init_memory_sqlite_model_str(
        self,
        mocked_generate: AsyncMock,
        mocked_init: AsyncMock,
    ) -> None:
        @init_memory_sqlite("app.models")
        async def run():
            return "foo"

        res = await run()
        self.assertEqual(res, "foo")
        mocked_init.assert_awaited_once()
        mocked_init.assert_called_once_with(
            db_url="sqlite://:memory:", modules={"models": ["app.models"]}
        )
        mocked_generate.assert_awaited_once()
