from typing import Type

from tests.testmodels import Tournament
from tortoise import Model, Tortoise
from tortoise.contrib import test


class Router:
    def db_for_read(self, model: Type[Model]):
        return "models"

    def db_for_write(self, model: Type[Model]):
        return "models"


class TestRouter(test.SimpleTestCase):
    async def setUp(self):
        if Tortoise._inited:
            await self._tearDownDB()
        db_config = test.getDBConfig(app_label="models", modules=["tests.testmodels"])
        await Tortoise.init(db_config, _create_db=True, routers=[Router])
        await Tortoise.generate_schemas()

    async def tearDown(self):
        await Tortoise._drop_databases()

    async def test_router(self):
        tournament = await Tournament.create(name="Tournament")
        tournament2 = await Tournament.get(name="Tournament")
        self.assertEqual(tournament.pk, tournament2.pk)
