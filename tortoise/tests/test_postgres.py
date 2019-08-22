"""
Test some postgres-specific features
"""
from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import OperationalError
from tortoise.tests.testmodels import Tournament


class TestTwoDatabases(test.SimpleTestCase):
    async def setUp(self):
        if Tortoise._inited:
            await self._tearDownDB()
        self.db_config = test.getDBConfig(app_label="models", modules=["tortoise.tests.testmodels"])
        if self.db_config["connections"]["models"]["engine"] != "tortoise.backends.asyncpg":
            raise test.SkipTest("PostgreSQL only")

    async def tearDown(self) -> None:
        if Tortoise._inited:
            await Tortoise._drop_databases()

    async def test_schema(self):
        from asyncpg.exceptions import InvalidSchemaNameError

        self.db_config["connections"]["models"]["credentials"]["schema"] = "mytestschema"
        await Tortoise.init(self.db_config, _create_db=True)

        with self.assertRaises(InvalidSchemaNameError):
            await Tortoise.generate_schemas()

        conn = Tortoise.get_connection("models")
        await conn.execute_script("CREATE SCHEMA mytestschema;")
        await Tortoise.generate_schemas()

        tournament = await Tournament.create(name="Test")
        await Tortoise.close_connections()

        del self.db_config["connections"]["models"]["credentials"]["schema"]
        await Tortoise.init(self.db_config)

        with self.assertRaises(OperationalError):
            await Tournament.filter(name="Test").first()

        conn = Tortoise.get_connection("models")
        res = await conn.execute_query(
            "SELECT id, name FROM mytestschema.tournament WHERE name='Test' LIMIT 1"
        )

        self.assertEqual(len(res), 1)
        self.assertEqual(tournament.id, res[0][0])
        self.assertEqual(tournament.name, res[0][1])
