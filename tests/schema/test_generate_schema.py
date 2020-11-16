# pylint: disable=C0301
import re

from asynctest.mock import CoroutineMock, patch

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
        self.sqls = ""
        self.post_sqls = ""
        self.engine = test.getDBConfig(app_label="models", modules=[])["connections"]["models"][
            "engine"
        ]

    async def tearDown(self):
        Tortoise._connections = {}
        await Tortoise._reset_apps()

    async def init_for(self, module: str, safe=False) -> None:
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
            self.sqls = get_schema_sql(Tortoise._connections["default"], safe).split(";\n")

    def get_sql(self, text: str) -> str:
        return re.sub(r"[ \t\n\r]+", " ", " ".join([sql for sql in self.sqls if text in sql]))

    async def test_noid(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql('"noid"')
        self.assertIn('"name" VARCHAR(255)', sql)
        self.assertIn('"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL', sql)

    async def test_minrelation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql('"minrelation"')
        self.assertIn(
            '"tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("id") ON DELETE CASCADE',
            sql,
        )
        self.assertNotIn("participants", sql)

        sql = self.get_sql('"minrelation_team"')
        self.assertIn(
            '"minrelation_id" INT NOT NULL REFERENCES "minrelation" ("id") ON DELETE CASCADE', sql
        )
        self.assertIn('"team_id" INT NOT NULL REFERENCES "team" ("id") ON DELETE CASCADE', sql)

    async def test_safe_generation(self):
        """Assert that the IF NOT EXISTS clause is included when safely generating schema."""
        await self.init_for("tests.testmodels", True)
        sql = self.get_sql("")
        self.assertIn("IF NOT EXISTS", sql)

    async def test_unsafe_generation(self):
        """Assert that the IF NOT EXISTS clause is not included when generating schema."""
        await self.init_for("tests.testmodels", False)
        sql = self.get_sql("")
        self.assertNotIn("IF NOT EXISTS", sql)

    async def test_cyclic(self):
        with self.assertRaisesRegex(
            ConfigurationError, "Can't create schema due to cyclic fk references"
        ):
            await self.init_for("tests.schema.models_cyclic")

    async def test_create_index(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("CREATE INDEX")
        self.assertIsNotNone(re.search(r"idx_tournament_created_\w+", sql))

    async def test_fk_bad_model_name(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'Foreign key accepts model name in format "app.Model"'
        ):
            await self.init_for("tests.schema.models_fk_1")

    async def test_fk_bad_on_delete(self):
        with self.assertRaisesRegex(
            ConfigurationError, "on_delete can only be CASCADE, RESTRICT or SET_NULL"
        ):
            await self.init_for("tests.schema.models_fk_2")

    async def test_fk_bad_null(self):
        with self.assertRaisesRegex(
            ConfigurationError, "If on_delete is SET_NULL, then field must have null=True set"
        ):
            await self.init_for("tests.schema.models_fk_3")

    async def test_o2o_bad_on_delete(self):
        with self.assertRaisesRegex(
            ConfigurationError, "on_delete can only be CASCADE, RESTRICT or SET_NULL"
        ):
            await self.init_for("tests.schema.models_o2o_2")

    async def test_o2o_bad_null(self):
        with self.assertRaisesRegex(
            ConfigurationError, "If on_delete is SET_NULL, then field must have null=True set"
        ):
            await self.init_for("tests.schema.models_o2o_3")

    async def test_m2m_bad_model_name(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'Foreign key accepts model name in format "app.Model"'
        ):
            await self.init_for("tests.schema.models_m2m_1")

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("comments")
        self.assertRegex(sql, r".*\/\* Upvotes done on the comment.*\*\/")
        self.assertRegex(sql, r".*\\n.*")
        self.assertIn("\\/", sql)

    async def test_schema_no_db_constraint(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_no_db_constraint")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            r"""CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50)
) /* The TEAMS! */;
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL  /* Tournament name */,
    "created" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP /* Created *\/'`\/* datetime */
) /* What Tournaments *\/'`\/* we have */;
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" VARCHAR(40),
    "token" VARCHAR(100) NOT NULL UNIQUE /* Unique token */,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
) /* This table contains a list of all the events */;
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL,
    "team_id" VARCHAR(50) NOT NULL
);
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL,
    "team_id" VARCHAR(50) NOT NULL
) /* How participants relate */;""",
        )

    async def test_schema(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE "company" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" TEXT NOT NULL,
    "uuid" CHAR(36) NOT NULL UNIQUE
);
CREATE TABLE "defaultpk" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "val" INT NOT NULL
);
CREATE TABLE "employee" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" TEXT NOT NULL,
    "company_id" CHAR(36) NOT NULL REFERENCES "company" ("uuid") ON DELETE CASCADE
);
CREATE TABLE "inheritedmodel" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "zero" INT NOT NULL,
    "one" VARCHAR(40),
    "new_field" VARCHAR(100) NOT NULL,
    "two" VARCHAR(40) NOT NULL,
    "name" TEXT NOT NULL
);
CREATE TABLE "sometable" (
    "sometable_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "some_chars_table" VARCHAR(255) NOT NULL,
    "fk_sometable" INT REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE INDEX "idx_sometable_some_ch_3d69eb" ON "sometable" ("some_chars_table");
CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
) /* The TEAMS! */;
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE "teamaddress" (
    "city" VARCHAR(50) NOT NULL  /* City */,
    "country" VARCHAR(50) NOT NULL  /* Country */,
    "street" VARCHAR(128) NOT NULL  /* Street Address */,
    "team_id" VARCHAR(50) NOT NULL  PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
) /* The Team's address */;
CREATE TABLE "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL  /* Tournament name */,
    "created" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP /* Created *\\/'`\\/* datetime */
) /* What Tournaments *\\/'`\\/* we have */;
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" VARCHAR(40),
    "token" VARCHAR(100) NOT NULL UNIQUE /* Unique token */,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE /* FK to tournament */,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
) /* This table contains a list of all the events */;
CREATE TABLE "venueinformation" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(128) NOT NULL,
    "capacity" INT NOT NULL  /* No. of seats */,
    "rent" REAL NOT NULL,
    "team_id" VARCHAR(50)  UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
CREATE TABLE "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
) /* How participants relate */;
""".strip(),
        )

    async def test_schema_safe(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=True)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE IF NOT EXISTS "company" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" TEXT NOT NULL,
    "uuid" CHAR(36) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "defaultpk" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "val" INT NOT NULL
);
CREATE TABLE IF NOT EXISTS "employee" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" TEXT NOT NULL,
    "company_id" CHAR(36) NOT NULL REFERENCES "company" ("uuid") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "inheritedmodel" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "zero" INT NOT NULL,
    "one" VARCHAR(40),
    "new_field" VARCHAR(100) NOT NULL,
    "two" VARCHAR(40) NOT NULL,
    "name" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "sometable" (
    "sometable_id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "some_chars_table" VARCHAR(255) NOT NULL,
    "fk_sometable" INT REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_sometable_some_ch_3d69eb" ON "sometable" ("some_chars_table");
CREATE TABLE IF NOT EXISTS "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
) /* The TEAMS! */;
CREATE INDEX IF NOT EXISTS "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX IF NOT EXISTS "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE IF NOT EXISTS "teamaddress" (
    "city" VARCHAR(50) NOT NULL  /* City */,
    "country" VARCHAR(50) NOT NULL  /* Country */,
    "street" VARCHAR(128) NOT NULL  /* Street Address */,
    "team_id" VARCHAR(50) NOT NULL  PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
) /* The Team's address */;
CREATE TABLE IF NOT EXISTS "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL  /* Tournament name */,
    "created" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP /* Created *\\/'`\\/* datetime */
) /* What Tournaments *\\/'`\\/* we have */;
CREATE INDEX IF NOT EXISTS "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE IF NOT EXISTS "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" VARCHAR(40),
    "token" VARCHAR(100) NOT NULL UNIQUE /* Unique token */,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE /* FK to tournament */,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
) /* This table contains a list of all the events */;
CREATE TABLE IF NOT EXISTS "venueinformation" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(128) NOT NULL,
    "capacity" INT NOT NULL  /* No. of seats */,
    "rent" REAL NOT NULL,
    "team_id" VARCHAR(50)  UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
) /* How participants relate */;
""".strip(),
        )


class TestGenerateSchemaMySQL(TestGenerateSchema):
    async def init_for(self, module: str, safe=False) -> None:
        try:
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
                                    "charset": "utf8mb4",
                                },
                            }
                        },
                        "apps": {"models": {"models": [module], "default_connection": "default"}},
                    }
                )
                self.sqls = get_schema_sql(Tortoise._connections["default"], safe).split("; ")
        except ImportError:
            raise test.SkipTest("aiomysql not installed")

    async def test_noid(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("`noid`")
        self.assertIn("`name` VARCHAR(255)", sql)
        self.assertIn("`id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT", sql)

    async def test_create_index(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("KEY")
        self.assertIsNotNone(re.search(r"idx_tournament_created_\w+", sql))

    async def test_minrelation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("`minrelation`")
        self.assertIn("`tournament_id` SMALLINT NOT NULL,", sql)
        self.assertIn(
            "FOREIGN KEY (`tournament_id`) REFERENCES `tournament` (`id`) ON DELETE CASCADE", sql
        )
        self.assertNotIn("participants", sql)

        sql = self.get_sql("`minrelation_team`")
        self.assertIn("`minrelation_id` INT NOT NULL", sql)
        self.assertIn(
            "FOREIGN KEY (`minrelation_id`) REFERENCES `minrelation` (`id`) ON DELETE CASCADE", sql
        )
        self.assertIn("`team_id` INT NOT NULL", sql)
        self.assertIn("FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE", sql)

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("comments")
        self.assertIn("COMMENT='Test Table comment'", sql)
        self.assertIn("COMMENT 'This column acts as it\\'s own comment'", sql)
        self.assertRegex(sql, r".*\\n.*")
        self.assertRegex(sql, r".*it\\'s.*")

    async def test_schema_no_db_constraint(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_no_db_constraint")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            r"""CREATE TABLE `team` (
    `name` VARCHAR(50) NOT NULL  PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL  COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL  COMMENT 'Created */\'`/* datetime' DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\'`/* we have';
CREATE TABLE `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `prize` DECIMAL(10,2),
    `token` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Unique token',
    `key` VARCHAR(100) NOT NULL,
    `tournament_id` SMALLINT NOT NULL,
    UNIQUE KEY `uid_event_name_c6f89f` (`name`, `prize`),
    UNIQUE KEY `uid_event_tournam_a5b730` (`tournament_id`, `key`)
) CHARACTER SET utf8mb4 COMMENT='This table contains a list of all the events';
CREATE TABLE `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE `teamevents` (
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL
) CHARACTER SET utf8mb4 COMMENT='How participants relate';""",
        )

    async def test_schema(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE `company` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `uuid` CHAR(36) NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
CREATE TABLE `defaultpk` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `val` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE `employee` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `company_id` CHAR(36) NOT NULL,
    CONSTRAINT `fk_employee_company_08999a42` FOREIGN KEY (`company_id`) REFERENCES `company` (`uuid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE `inheritedmodel` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `zero` INT NOT NULL,
    `one` VARCHAR(40),
    `new_field` VARCHAR(100) NOT NULL,
    `two` VARCHAR(40) NOT NULL,
    `name` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE `sometable` (
    `sometable_id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `some_chars_table` VARCHAR(255) NOT NULL,
    `fk_sometable` INT,
    CONSTRAINT `fk_sometabl_sometabl_6efae9bd` FOREIGN KEY (`fk_sometable`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    KEY `idx_sometable_some_ch_3d69eb` (`some_chars_table`)
) CHARACTER SET utf8mb4;
CREATE TABLE `team` (
    `name` VARCHAR(50) NOT NULL  PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    CONSTRAINT `fk_team_team_9c77cd8f` FOREIGN KEY (`manager_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE `teamaddress` (
    `city` VARCHAR(50) NOT NULL  COMMENT 'City',
    `country` VARCHAR(50) NOT NULL  COMMENT 'Country',
    `street` VARCHAR(128) NOT NULL  COMMENT 'Street Address',
    `team_id` VARCHAR(50) NOT NULL  PRIMARY KEY,
    CONSTRAINT `fk_teamaddr_team_1c78d737` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='The Team\\'s address';
CREATE TABLE `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL  COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL  COMMENT 'Created */\\'`/* datetime' DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\\'`/* we have';
CREATE TABLE `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `prize` DECIMAL(10,2),
    `token` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Unique token',
    `key` VARCHAR(100) NOT NULL,
    `tournament_id` SMALLINT NOT NULL COMMENT 'FK to tournament',
    UNIQUE KEY `uid_event_name_c6f89f` (`name`, `prize`),
    UNIQUE KEY `uid_event_tournam_a5b730` (`tournament_id`, `key`),
    CONSTRAINT `fk_event_tourname_51c2b82d` FOREIGN KEY (`tournament_id`) REFERENCES `tournament` (`tid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='This table contains a list of all the events';
CREATE TABLE `venueinformation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `capacity` INT NOT NULL  COMMENT 'No. of seats',
    `rent` DOUBLE NOT NULL,
    `team_id` VARCHAR(50)  UNIQUE,
    CONSTRAINT `fk_venueinf_team_198af929` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE `sometable_self` (
    `backward_sts` INT NOT NULL,
    `sts_forward` INT NOT NULL,
    FOREIGN KEY (`backward_sts`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    FOREIGN KEY (`sts_forward`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`team_rel_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE `teamevents` (
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`event_id`) REFERENCES `event` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL
) CHARACTER SET utf8mb4 COMMENT='How participants relate';
""".strip(),
        )

    async def test_schema_safe(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=True)

        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE IF NOT EXISTS `company` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `uuid` CHAR(36) NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `defaultpk` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `val` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `employee` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `company_id` CHAR(36) NOT NULL,
    CONSTRAINT `fk_employee_company_08999a42` FOREIGN KEY (`company_id`) REFERENCES `company` (`uuid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `inheritedmodel` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `zero` INT NOT NULL,
    `one` VARCHAR(40),
    `new_field` VARCHAR(100) NOT NULL,
    `two` VARCHAR(40) NOT NULL,
    `name` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sometable` (
    `sometable_id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `some_chars_table` VARCHAR(255) NOT NULL,
    `fk_sometable` INT,
    CONSTRAINT `fk_sometabl_sometabl_6efae9bd` FOREIGN KEY (`fk_sometable`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    KEY `idx_sometable_some_ch_3d69eb` (`some_chars_table`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `team` (
    `name` VARCHAR(50) NOT NULL  PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    CONSTRAINT `fk_team_team_9c77cd8f` FOREIGN KEY (`manager_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE IF NOT EXISTS `teamaddress` (
    `city` VARCHAR(50) NOT NULL  COMMENT 'City',
    `country` VARCHAR(50) NOT NULL  COMMENT 'Country',
    `street` VARCHAR(128) NOT NULL  COMMENT 'Street Address',
    `team_id` VARCHAR(50) NOT NULL  PRIMARY KEY,
    CONSTRAINT `fk_teamaddr_team_1c78d737` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='The Team\\'s address';
CREATE TABLE IF NOT EXISTS `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL  COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL  COMMENT 'Created */\\'`/* datetime' DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\\'`/* we have';
CREATE TABLE IF NOT EXISTS `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `prize` DECIMAL(10,2),
    `token` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Unique token',
    `key` VARCHAR(100) NOT NULL,
    `tournament_id` SMALLINT NOT NULL COMMENT 'FK to tournament',
    UNIQUE KEY `uid_event_name_c6f89f` (`name`, `prize`),
    UNIQUE KEY `uid_event_tournam_a5b730` (`tournament_id`, `key`),
    CONSTRAINT `fk_event_tourname_51c2b82d` FOREIGN KEY (`tournament_id`) REFERENCES `tournament` (`tid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='This table contains a list of all the events';
CREATE TABLE IF NOT EXISTS `venueinformation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `capacity` INT NOT NULL  COMMENT 'No. of seats',
    `rent` DOUBLE NOT NULL,
    `team_id` VARCHAR(50)  UNIQUE,
    CONSTRAINT `fk_venueinf_team_198af929` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sometable_self` (
    `backward_sts` INT NOT NULL,
    `sts_forward` INT NOT NULL,
    FOREIGN KEY (`backward_sts`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    FOREIGN KEY (`sts_forward`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`team_rel_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `teamevents` (
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`event_id`) REFERENCES `event` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL
) CHARACTER SET utf8mb4 COMMENT='How participants relate';
""".strip(),
        )


class TestGenerateSchemaPostgresSQL(TestGenerateSchema):
    async def init_for(self, module: str, safe=False) -> None:
        try:
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
        except ImportError:
            raise test.SkipTest("asyncpg not installed")

    async def test_noid(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql('"noid"')
        self.assertIn('"name" VARCHAR(255)', sql)
        self.assertIn('"id" SERIAL NOT NULL PRIMARY KEY', sql)

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("comments")
        self.assertIn("COMMENT ON TABLE \"comments\" IS 'Test Table comment'", sql)
        self.assertIn(
            'COMMENT ON COLUMN "comments"."escaped_comment_field" IS '
            "'This column acts as it''s own comment'",
            sql,
        )
        self.assertIn(
            'COMMENT ON COLUMN "comments"."multiline_comment" IS \'Some \\n comment\'', sql
        )

    async def test_schema_no_db_constraint(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_no_db_constraint")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            r"""CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50)
);
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
COMMENT ON COLUMN "team"."name" IS 'The TEAM name (and PK)';
COMMENT ON TABLE "team" IS 'The TEAMS!';
CREATE TABLE "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" DECIMAL(10,2),
    "token" VARCHAR(100) NOT NULL UNIQUE,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
);
COMMENT ON COLUMN "event"."id" IS 'Event ID';
COMMENT ON COLUMN "event"."token" IS 'Unique token';
COMMENT ON COLUMN "event"."tournament_id" IS 'FK to tournament';
COMMENT ON TABLE "event" IS 'This table contains a list of all the events';
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL,
    "team_id" VARCHAR(50) NOT NULL
);
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL,
    "team_id" VARCHAR(50) NOT NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';""",
        )

    async def test_schema(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE "company" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "uuid" UUID NOT NULL UNIQUE
);
CREATE TABLE "defaultpk" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "val" INT NOT NULL
);
CREATE TABLE "employee" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "company_id" UUID NOT NULL REFERENCES "company" ("uuid") ON DELETE CASCADE
);
CREATE TABLE "inheritedmodel" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "zero" INT NOT NULL,
    "one" VARCHAR(40),
    "new_field" VARCHAR(100) NOT NULL,
    "two" VARCHAR(40) NOT NULL,
    "name" TEXT NOT NULL
);
CREATE TABLE "sometable" (
    "sometable_id" SERIAL NOT NULL PRIMARY KEY,
    "some_chars_table" VARCHAR(255) NOT NULL,
    "fk_sometable" INT REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE INDEX "idx_sometable_some_ch_3d69eb" ON "sometable" ("some_chars_table");
CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
COMMENT ON COLUMN "team"."name" IS 'The TEAM name (and PK)';
COMMENT ON TABLE "team" IS 'The TEAMS!';
CREATE TABLE "teamaddress" (
    "city" VARCHAR(50) NOT NULL,
    "country" VARCHAR(50) NOT NULL,
    "street" VARCHAR(128) NOT NULL,
    "team_id" VARCHAR(50) NOT NULL  PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "teamaddress"."city" IS 'City';
COMMENT ON COLUMN "teamaddress"."country" IS 'Country';
COMMENT ON COLUMN "teamaddress"."street" IS 'Street Address';
COMMENT ON TABLE "teamaddress" IS 'The Team''s address';
CREATE TABLE "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" DECIMAL(10,2),
    "token" VARCHAR(100) NOT NULL UNIQUE,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
);
COMMENT ON COLUMN "event"."id" IS 'Event ID';
COMMENT ON COLUMN "event"."token" IS 'Unique token';
COMMENT ON COLUMN "event"."tournament_id" IS 'FK to tournament';
COMMENT ON TABLE "event" IS 'This table contains a list of all the events';
CREATE TABLE "venueinformation" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(128) NOT NULL,
    "capacity" INT NOT NULL,
    "rent" DOUBLE PRECISION NOT NULL,
    "team_id" VARCHAR(50)  UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON COLUMN "venueinformation"."capacity" IS 'No. of seats';
CREATE TABLE "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
""".strip(),
        )

    async def test_schema_safe(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=True)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE IF NOT EXISTS "company" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "uuid" UUID NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "defaultpk" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "val" INT NOT NULL
);
CREATE TABLE IF NOT EXISTS "employee" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "company_id" UUID NOT NULL REFERENCES "company" ("uuid") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "inheritedmodel" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "zero" INT NOT NULL,
    "one" VARCHAR(40),
    "new_field" VARCHAR(100) NOT NULL,
    "two" VARCHAR(40) NOT NULL,
    "name" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "sometable" (
    "sometable_id" SERIAL NOT NULL PRIMARY KEY,
    "some_chars_table" VARCHAR(255) NOT NULL,
    "fk_sometable" INT REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_sometable_some_ch_3d69eb" ON "sometable" ("some_chars_table");
CREATE TABLE IF NOT EXISTS "team" (
    "name" VARCHAR(50) NOT NULL  PRIMARY KEY,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX IF NOT EXISTS "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
COMMENT ON COLUMN "team"."name" IS 'The TEAM name (and PK)';
COMMENT ON TABLE "team" IS 'The TEAMS!';
CREATE TABLE IF NOT EXISTS "teamaddress" (
    "city" VARCHAR(50) NOT NULL,
    "country" VARCHAR(50) NOT NULL,
    "street" VARCHAR(128) NOT NULL,
    "team_id" VARCHAR(50) NOT NULL  PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "teamaddress"."city" IS 'City';
COMMENT ON COLUMN "teamaddress"."country" IS 'Country';
COMMENT ON COLUMN "teamaddress"."street" IS 'Street Address';
COMMENT ON TABLE "teamaddress" IS 'The Team''s address';
CREATE TABLE IF NOT EXISTS "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE IF NOT EXISTS "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "prize" DECIMAL(10,2),
    "token" VARCHAR(100) NOT NULL UNIQUE,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
);
COMMENT ON COLUMN "event"."id" IS 'Event ID';
COMMENT ON COLUMN "event"."token" IS 'Unique token';
COMMENT ON COLUMN "event"."tournament_id" IS 'FK to tournament';
COMMENT ON TABLE "event" IS 'This table contains a list of all the events';
CREATE TABLE IF NOT EXISTS "venueinformation" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(128) NOT NULL,
    "capacity" INT NOT NULL,
    "rent" DOUBLE PRECISION NOT NULL,
    "team_id" VARCHAR(50)  UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON COLUMN "venueinformation"."capacity" IS 'No. of seats';
CREATE TABLE IF NOT EXISTS "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
""".strip(),
        )
