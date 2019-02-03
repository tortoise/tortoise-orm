import re

from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError
from tortoise.utils import get_schema_sql


class TestGenerateSchema(test.SimpleTestCase):
    async def setUp(self):
        try:
            Tortoise.apps = {}
            Tortoise._connections = {}
            Tortoise._inited = False
        except ConfigurationError:
            pass
        Tortoise._inited = False

    async def tearDown(self):
        await Tortoise.close_connections()
        await Tortoise._reset_apps()

    async def init_for(self, module: str, safe=False) -> None:
        await Tortoise.init({
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {
                        "file_path": ":memory:",
                    }
                }
            },
            "apps": {
                "models": {
                    "models": [
                        module,
                    ],
                    "default_connection": "default"
                }
            }
        })
        self.sqls = get_schema_sql(Tortoise._connections['default'], safe).split('; ')

    def get_sql(self, text: str) -> str:
        return [sql for sql in self.sqls if text in sql][0]

    async def test_noid(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql('"noid"')
        self.assertIn('"name" VARCHAR(255)', sql)
        self.assertIn('"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL', sql)

    async def test_minrelation(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql('"minrelation"')
        self.assertIn(
            '"tournament_id" INT NOT NULL REFERENCES "tournament" (id) ON DELETE CASCADE', sql)
        self.assertNotIn('participants', sql)

        sql = self.get_sql('"minrelation_team"')
        self.assertIn(
            '"minrelation_id" INT NOT NULL REFERENCES "minrelation" (id) ON DELETE CASCADE', sql)
        self.assertIn('"team_id" INT NOT NULL REFERENCES "team" (id) ON DELETE CASCADE', sql)

    async def test_safe_generation(self):
        """Assert that the IF NOT EXISTS clause is included when safely generating schema."""
        await self.init_for("tortoise.tests.testmodels", True)
        sql = self.get_sql("")
        self.assertIn("IF NOT EXISTS", sql)

    async def test_unsafe_generation(self):
        """Assert that the IF NOT EXISTS clause is not included when generating schema."""
        await self.init_for("tortoise.tests.testmodels", False)
        sql = self.get_sql("")
        self.assertNotIn("IF NOT EXISTS", sql)

    async def test_cyclic(self):
        with self.assertRaisesRegex(ConfigurationError,
                                    "Can't create schema due to cyclic fk references"):
            await self.init_for("tortoise.tests.testmodels_cyclic")

    async def test_create_index(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql("CREATE INDEX")
        self.assertIsNotNone(re.search(r"tournament_created_\w+_idx", sql))

    async def test_index_safe(self):
        await self.init_for("tortoise.tests.testmodels", safe=True)
        test.checkCapability("default", safe_indexes=True)
        sql = self.get_sql("CREATE INDEX")
        self.assertIn("IF NOT EXISTS", sql)

    async def test_safe_index_not_created_if_not_supported(self):
        await self.init_for("tortoise.tests.testmodels", safe=True)
        test.checkCapability("default", safe_indexes=False)
        sql = self.get_sql("")
        self.assertNotIn("CREATE INDEX", sql)
