import re

from asynctest.mock import CoroutineMock, patch

from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError
from tortoise.utils import generate_post_table_sql, get_schema_sql


class TestGenerateSchema(test.SimpleTestCase):
    async def setUp(self):
        try:
            Tortoise.apps = {}
            Tortoise._connections = {}
            Tortoise._inited = False
        except ConfigurationError:
            pass
        Tortoise._inited = False
        self.sqls = ""
        self.engine = test.getDBConfig(app_label="models", modules=[])["connections"]["models"][
            "engine"
        ]

    async def tearDown(self):
        Tortoise._connections = {}
        await Tortoise._reset_apps()

    async def init_for(self, module: str, safe=False) -> None:
        if self.engine != "tortoise.backends.sqlite":
            raise test.SkipTest("sqlite only")
        with patch(
            "tortoise.backends.sqlite.client.SqliteClient.create_connection", new=CoroutineMock()
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {"models": {"models": [module], "default_connection": "default"}},
                }
            )
            self.sqls = get_schema_sql(Tortoise._connections["default"], safe).split("; ")
            self.post_sqls = generate_post_table_sql(Tortoise._connections["default"], safe).split(
                "; "
            )

    def get_sql(self, text: str) -> str:
        return re.sub(r"[ \t\n\r]+", " ", [sql for sql in self.sqls if text in sql][0])

    def get_post_sql(self, text: str) -> str:
        return re.sub(r"[ \t\n\r]+", " ", [sql for sql in self.post_sqls if text in sql][0])

    async def test_noid(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql('"noid"')
        self.assertIn('"name" VARCHAR(255)', sql)
        self.assertIn('"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL', sql)

    async def test_minrelation(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql('"minrelation"')
        self.assertIn(
            '"tournament_id" INT NOT NULL REFERENCES "tournament" (id) ON DELETE CASCADE', sql
        )
        self.assertNotIn("participants", sql)

        sql = self.get_sql('"minrelation_team"')
        self.assertIn(
            '"minrelation_id" INT NOT NULL REFERENCES "minrelation" (id) ON DELETE CASCADE', sql
        )
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
        with self.assertRaisesRegex(
            ConfigurationError, "Can't create schema due to cyclic fk references"
        ):
            await self.init_for("tortoise.tests.models_cyclic")

    def continue_if_safe_indexes(self, supported: bool):
        db = Tortoise.get_connection("default")
        if db.capabilities.safe_indexes != supported:
            raise test.SkipTest("safe_indexes != {}".format(supported))

    async def test_create_index(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql("CREATE INDEX")
        self.assertIsNotNone(re.search(r"tournament_created_\w+_idx", sql))

    async def test_index_safe(self):
        await self.init_for("tortoise.tests.testmodels", safe=True)
        self.continue_if_safe_indexes(supported=True)
        sql = self.get_sql("CREATE INDEX")
        self.assertIn("IF NOT EXISTS", sql)

    async def test_safe_index_not_created_if_not_supported(self):
        await self.init_for("tortoise.tests.testmodels", safe=True)
        self.continue_if_safe_indexes(supported=False)
        sql = self.get_sql("")
        self.assertNotIn("CREATE INDEX", sql)

    async def test_fk_bad_model_name(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'Foreign key accepts model name in format "app.Model"'
        ):
            await self.init_for("tortoise.tests.models_fk_1")

    async def test_fk_bad_on_delete(self):
        with self.assertRaisesRegex(
            ConfigurationError, "on_delete can only be CASCADE, RESTRICT or SET_NULL"
        ):
            await self.init_for("tortoise.tests.models_fk_2")

    async def test_fk_bad_null(self):
        with self.assertRaisesRegex(
            ConfigurationError, "If on_delete is SET_NULL, then field must have null=True set"
        ):
            await self.init_for("tortoise.tests.models_fk_3")

    async def test_m2m_bad_model_name(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'Foreign key accepts model name in format "app.Model"'
        ):
            await self.init_for("tortoise.tests.models_m2m_1")

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tortoise.tests.testmodels", safe=True)
        self.continue_if_safe_indexes(supported=False)
        sql = self.get_sql("comments")
        self.assertRegex(sql, r".*\/\* Upvotes done on the comment.*\*\/")
        self.assertRegex(sql, r".*\\n.*")
        self.assertRegex(sql, r".*it\'s.*")


class TestGenerateSchemaMySQL(TestGenerateSchema):
    async def init_for(self, module: str, safe=False) -> None:
        if self.engine != "tortoise.backends.mysql":
            raise test.SkipTest("mysql only")
        with patch("aiomysql.create_pool", new=CoroutineMock()):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.mysql",
                            "credentials": {
                                "database": "test",
                                "host": "127.0.0.1",
                                "password": "foomip",
                                "port": 3306,
                                "user": "root",
                                "connect_timeout": 1.5,
                                "charset": "utf-8",
                            },
                        }
                    },
                    "apps": {"models": {"models": [module], "default_connection": "default"}},
                }
            )
            self.sqls = get_schema_sql(Tortoise._connections["default"], safe).split("; ")

    async def test_noid(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql("`noid`")
        self.assertIn("`name` VARCHAR(255)", sql)
        self.assertIn("`id` INT UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT", sql)

    async def test_minrelation(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql("`minrelation`")
        self.assertIn(
            "`tournament_id` INT NOT NULL REFERENCES `tournament` (`id`) ON DELETE CASCADE", sql
        )
        self.assertNotIn("participants", sql)

        sql = self.get_sql("`minrelation_team`")
        self.assertIn(
            "`minrelation_id` INT NOT NULL REFERENCES `minrelation` (`id`) ON DELETE CASCADE", sql
        )
        self.assertIn("`team_id` INT NOT NULL REFERENCES `team` (`id`) ON DELETE CASCADE", sql)

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tortoise.tests.testmodels", safe=True)
        self.continue_if_safe_indexes(supported=False)
        sql = self.get_sql("comments")
        self.assertIn("COMMENT=", sql)
        self.assertIn("COMMENT ", sql)
        self.assertRegex(sql, r".*\\n.*")
        self.assertRegex(sql, r".*it\\'s.*")


class TestGenerateSchemaPostgresSQL(TestGenerateSchema):
    async def init_for(self, module: str, safe=False) -> None:
        if self.engine != "tortoise.backends.asyncpg":
            raise test.SkipTest("asyncpg only")
        with patch("asyncpg.create_pool", new=CoroutineMock()):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.asyncpg",
                            "credentials": {
                                "database": "test",
                                "host": "127.0.0.1",
                                "password": "foomip",
                                "port": 3306,
                                "user": "root",
                            },
                        }
                    },
                    "apps": {"models": {"models": [module], "default_connection": "default"}},
                }
            )
            self.sqls = get_schema_sql(Tortoise._connections["default"], safe).split("; ")

    async def test_noid(self):
        await self.init_for("tortoise.tests.testmodels")
        sql = self.get_sql('"noid"')
        self.assertIn('"name" VARCHAR(255)', sql)
        self.assertIn('"id" SERIAL NOT NULL PRIMARY KEY', sql)

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tortoise.tests.testmodels", safe=True)
        self.continue_if_safe_indexes(supported=False)
        sql = self.get_post_sql("comments")
        self.assertIn("COMMENT ON TABLE", sql)
        self.assertIn("COMMENT ON COLUMN", sql)
        self.assertRegex(sql, r"COMMENT ON TABLE comments IS.*")
        self.assertRegex(
            sql, r"COMMENT ON COLUMN comments\..* IS.*;.*COMMENT ON COLUMN comments\..* IS.*"
        )
        self.assertRegex(sql, r".*\\n.*")
        self.assertRegex(sql, r".*it\'s.*")
