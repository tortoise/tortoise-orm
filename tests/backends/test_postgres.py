"""
Test some PostgreSQL-specific features
"""

import ssl

from tests.testmodels import Tournament
from tortoise import Tortoise, connections
from tortoise.contrib import test
from tortoise.exceptions import OperationalError


class TestPostgreSQL(test.SimpleTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        if Tortoise._inited:
            await self._tearDownDB()
        self.db_config = test.getDBConfig(app_label="models", modules=["tests.testmodels"])
        if not self.is_asyncpg and not self.is_psycopg:
            raise test.SkipTest("PostgreSQL only")

    @property
    def is_psycopg(self) -> bool:
        return self.db_config["connections"]["models"]["engine"] == "tortoise.backends.psycopg"

    @property
    def is_asyncpg(self) -> bool:
        return self.db_config["connections"]["models"]["engine"] == "tortoise.backends.asyncpg"

    async def asyncTearDown(self) -> None:
        if Tortoise._inited:
            await Tortoise._drop_databases()
        await super().asyncTearDown()

    async def test_schema(self):
        if self.is_asyncpg:
            from asyncpg.exceptions import InvalidSchemaNameError
        else:
            from psycopg.errors import InvalidSchemaName as InvalidSchemaNameError

        self.db_config["connections"]["models"]["credentials"]["schema"] = "mytestschema"
        await Tortoise.init(self.db_config, _create_db=True)

        with self.assertRaises(InvalidSchemaNameError):
            await Tortoise.generate_schemas()

        conn = connections.get("models")
        await conn.execute_script("CREATE SCHEMA mytestschema;")
        await Tortoise.generate_schemas()

        tournament = await Tournament.create(name="Test")
        await connections.close_all()

        del self.db_config["connections"]["models"]["credentials"]["schema"]
        await Tortoise.init(self.db_config)

        with self.assertRaises(OperationalError):
            await Tournament.filter(name="Test").first()

        conn = connections.get("models")
        _, res = await conn.execute_query(
            "SELECT id, name FROM mytestschema.tournament WHERE name='Test' LIMIT 1"
        )

        self.assertEqual(len(res), 1)
        self.assertEqual(tournament.id, res[0]["id"])
        self.assertEqual(tournament.name, res[0]["name"])

    async def test_ssl_true(self):
        self.db_config["connections"]["models"]["credentials"]["ssl"] = True
        try:
            await Tortoise.init(self.db_config, _create_db=True)
        except (ConnectionError, ssl.SSLError):
            pass
        else:
            self.assertFalse(True, "Expected ConnectionError or SSLError")

    async def test_ssl_custom(self):
        # Expect connectionerror or pass
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.db_config["connections"]["models"]["credentials"]["ssl"] = ctx
        try:
            await Tortoise.init(self.db_config, _create_db=True)
        except ConnectionError:
            pass

    async def test_application_name(self):
        self.db_config["connections"]["models"]["credentials"][
            "application_name"
        ] = "mytest_application"
        await Tortoise.init(self.db_config, _create_db=True)

        conn = connections.get("models")
        _, res = await conn.execute_query(
            "SELECT application_name FROM pg_stat_activity WHERE pid = pg_backend_pid()"
        )

        self.assertEqual(len(res), 1)
        self.assertEqual("mytest_application", res[0]["application_name"])
