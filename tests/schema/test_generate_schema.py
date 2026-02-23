# pylint: disable=C0301
import os
import re
from unittest.mock import MagicMock, patch

import pytest

from tortoise import Tortoise, connections
from tortoise.backends.base.config_generator import generate_config
from tortoise.context import TortoiseContext, get_current_context
from tortoise.exceptions import ConfigurationError
from tortoise.utils import get_schema_sql

# Save original classproperties before any test can shadow them
_original_apps_prop = Tortoise.__dict__["apps"]
_original_inited_prop = Tortoise.__dict__["_inited"]


# Safe schema SQL expected for SQLite
SAFE_SCHEMA_SQL = """
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
    "name" VARCHAR(50) NOT NULL PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
) /* The TEAMS! */;
CREATE INDEX IF NOT EXISTS "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX IF NOT EXISTS "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE IF NOT EXISTS "teamaddress" (
    "city" VARCHAR(50) NOT NULL /* City */,
    "country" VARCHAR(50) NOT NULL /* Country */,
    "street" VARCHAR(128) NOT NULL /* Street Address */,
    "team_id" VARCHAR(50) NOT NULL PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
) /* The Team's address */;
CREATE TABLE IF NOT EXISTS "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL /* Tournament name */,
    "created" TIMESTAMP NOT NULL /* Created *\\/'`\\/* datetime */
) /* What Tournaments *\\/'`\\/* we have */;
CREATE INDEX IF NOT EXISTS "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE IF NOT EXISTS "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL,
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
    "capacity" INT NOT NULL /* No. of seats */,
    "rent" REAL NOT NULL,
    "team_id" VARCHAR(50) UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_sometable_s_backwar_fc8fc8" ON "sometable_self" ("backward_sts", "sts_forward");
CREATE TABLE IF NOT EXISTS "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE IF NOT EXISTS "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
) /* How participants relate */;
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");
""".strip()


async def _reset_tortoise():
    """Helper to reset Tortoise state before each test.

    Note: We MUST NOT set Tortoise.apps = None or Tortoise._inited = False
    because these are classproperties and setting them shadows the property
    with a class attribute, breaking future access.
    """
    # Restore original classproperties if they were shadowed
    if not isinstance(Tortoise.__dict__.get("apps"), type(_original_apps_prop)):
        type.__setattr__(Tortoise, "apps", _original_apps_prop)
    if not isinstance(Tortoise.__dict__.get("_inited"), type(_original_inited_prop)):
        type.__setattr__(Tortoise, "_inited", _original_inited_prop)

    # Get the current context and properly reset it
    ctx = get_current_context()
    if ctx is not None:
        # Clear db_config first to prevent close_all from trying to import bad backends
        if ctx._connections is not None:
            # Clear storage without closing (to avoid importing bad backends)
            ctx._connections._storage.clear()
            ctx._connections._db_config = None
            ctx._connections = None
        ctx._apps = None
        ctx._inited = False
        ctx._default_connection = None
    else:
        # No context exists - create one for the test
        ctx = TortoiseContext()
        ctx.__enter__()


async def _teardown_tortoise():
    """Helper to teardown Tortoise state after each test."""
    await Tortoise._reset_apps()


def _get_engine():
    """Get the current test engine."""
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")
    config = generate_config(db_url, app_modules={"models": []}, connection_label="models")
    return config["connections"]["models"]["engine"]


def _get_sql(sqls: list[str], text: str) -> str:
    """Get SQL statement containing the given text."""
    return re.sub(r"[ \t\n\r]+", " ", " ".join([sql for sql in sqls if text in sql]))


# ============================================================================
# SQLite Tests
# ============================================================================


async def _init_for_sqlite(module: str, safe: bool = False) -> list[str]:
    """Initialize Tortoise for SQLite and return SQL statements."""
    with patch("tortoise.backends.sqlite.client.SqliteClient.create_connection", new=MagicMock()):
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
        return get_schema_sql(connections.get("default"), safe).split(";\n")


@pytest.mark.asyncio
async def test_noid():
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.testmodels")
        sql = _get_sql(sqls, '"noid"')
        assert '"name" VARCHAR(255)' in sql
        assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_minrelation():
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.testmodels")
        sql = _get_sql(sqls, '"minrelation"')
        assert (
            '"tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("id") ON DELETE CASCADE'
            in sql
        )
        assert "participants" not in sql

        sql = _get_sql(sqls, '"minrelation_team"')
        assert (
            '"minrelation_id" INT NOT NULL REFERENCES "minrelation" ("id") ON DELETE CASCADE' in sql
        )
        assert '"team_id" INT NOT NULL REFERENCES "team" ("id") ON DELETE CASCADE' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_safe_generation():
    """Assert that the IF NOT EXISTS clause is included when safely generating schema."""
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.testmodels", True)
        sql = _get_sql(sqls, "")
        assert "IF NOT EXISTS" in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_unsafe_generation():
    """Assert that the IF NOT EXISTS clause is not included when generating schema."""
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.testmodels", False)
        sql = _get_sql(sqls, "")
        assert "IF NOT EXISTS" not in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_cyclic():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match="Can't create schema due to cyclic fk references"
        ):
            await _init_for_sqlite("tests.schema.models_cyclic")
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_create_index():
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.testmodels")
        sql = _get_sql(sqls, "CREATE INDEX")
        assert re.search(r"idx_tournament_created_\w+", sql) is not None
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_create_index_with_custom_name():
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.testmodels")
        sql = _get_sql(sqls, "f3")
        assert "model_with_indexes__f3" in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_fk_bad_model_name():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='ForeignKeyField accepts model name in format "app.Model"'
        ):
            await _init_for_sqlite("tests.schema.models_fk_1")
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_fk_bad_on_delete():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError,
            match="on_delete can only be CASCADE, RESTRICT, SET_NULL, SET_DEFAULT or NO_ACTION",
        ):
            await _init_for_sqlite("tests.schema.models_fk_2")
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_fk_bad_null():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match="If on_delete is SET_NULL, then field must have null=True set"
        ):
            await _init_for_sqlite("tests.schema.models_fk_3")
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_o2o_bad_on_delete():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError,
            match="on_delete can only be CASCADE, RESTRICT, SET_NULL, SET_DEFAULT or NO_ACTION",
        ):
            await _init_for_sqlite("tests.schema.models_o2o_2")
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_o2o_bad_null():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match="If on_delete is SET_NULL, then field must have null=True set"
        ):
            await _init_for_sqlite("tests.schema.models_o2o_3")
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_m2m_bad_model_name():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='ManyToManyField accepts model name in format "app.Model"'
        ):
            await _init_for_sqlite("tests.schema.models_m2m_1")
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_multi_m2m_fields_in_a_model():
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.schema.models_m2m_2")
        sql = _get_sql(sqls, "CASCADE")
        assert not re.search(r'REFERENCES [`"]three_one[`"]', sql)
        assert not re.search(r'REFERENCES [`"]three_two[`"]', sql)
        assert re.search(r'REFERENCES [`"](one|two|three)[`"]', sql)
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_table_and_row_comment_generation():
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.testmodels")
        sql = _get_sql(sqls, "comments")
        assert re.search(r".*\/\* Upvotes done on the comment.*\*\/", sql)
        assert re.search(r".*\\n.*", sql)
        assert "\\/" in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_schema_no_db_constraint():
    await _reset_tortoise()
    try:
        await _init_for_sqlite("tests.schema.models_no_db_constraint")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == r"""CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50)
) /* The TEAMS! */;
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL /* Tournament name */,
    "created" TIMESTAMP NOT NULL /* Created *\/'`\/* datetime */
) /* What Tournaments *\/'`\/* we have */;
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL,
    "prize" VARCHAR(40),
    "token" VARCHAR(100) NOT NULL UNIQUE /* Unique token */,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL /* FK to tournament */,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
) /* This table contains a list of all the events */;
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL,
    "team_id" VARCHAR(50) NOT NULL
);
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL,
    "team_id" VARCHAR(50) NOT NULL
) /* How participants relate */;
CREATE UNIQUE INDEX "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_schema():
    await _reset_tortoise()
    try:
        await _init_for_sqlite("tests.schema.models_schema_create")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == """
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
    "name" VARCHAR(50) NOT NULL PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
) /* The TEAMS! */;
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE "teamaddress" (
    "city" VARCHAR(50) NOT NULL /* City */,
    "country" VARCHAR(50) NOT NULL /* Country */,
    "street" VARCHAR(128) NOT NULL /* Street Address */,
    "team_id" VARCHAR(50) NOT NULL PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
) /* The Team's address */;
CREATE TABLE "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL /* Tournament name */,
    "created" TIMESTAMP NOT NULL /* Created *\\/'`\\/* datetime */
) /* What Tournaments *\\/'`\\/* we have */;
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL,
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
    "capacity" INT NOT NULL /* No. of seats */,
    "rent" REAL NOT NULL,
    "team_id" VARCHAR(50) UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
CREATE TABLE "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_sometable_s_backwar_fc8fc8" ON "sometable_self" ("backward_sts", "sts_forward");
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
) /* How participants relate */;
CREATE UNIQUE INDEX "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_schema_safe():
    await _reset_tortoise()
    try:
        await _init_for_sqlite("tests.schema.models_schema_create")
        sql = get_schema_sql(connections.get("default"), safe=True)
        assert sql.strip() == SAFE_SCHEMA_SQL
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_m2m_no_auto_create():
    await _reset_tortoise()
    try:
        await _init_for_sqlite("tests.schema.models_no_auto_create_m2m")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == r"""CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL PRIMARY KEY /* The TEAM name (and PK) */,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
) /* The TEAMS! */;
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
CREATE TABLE "tournament" (
    "tid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL /* Tournament name */,
    "created" TIMESTAMP NOT NULL /* Created *\/'`\/* datetime */
) /* What Tournaments *\/'`\/* we have */;
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
CREATE TABLE "event" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* Event ID */,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMP NOT NULL,
    "prize" VARCHAR(40),
    "token" VARCHAR(100) NOT NULL UNIQUE /* Unique token */,
    "key" VARCHAR(100) NOT NULL,
    "tournament_id" SMALLINT NOT NULL REFERENCES "tournament" ("tid") ON DELETE CASCADE /* FK to tournament */,
    CONSTRAINT "uid_event_name_c6f89f" UNIQUE ("name", "prize"),
    CONSTRAINT "uid_event_tournam_a5b730" UNIQUE ("tournament_id", "key")
) /* This table contains a list of all the events */;
CREATE TABLE "teamevents" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "score" INT NOT NULL,
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    CONSTRAINT "uid_teamevents_team_id_9e89fc" UNIQUE ("team_id", "event_id")
) /* How participants relate */;
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
""".strip()
        )
    finally:
        await _teardown_tortoise()


# ============================================================================
# MySQL Tests
# ============================================================================


async def _init_for_mysql(module: str, safe: bool = False) -> list[str]:
    """Initialize Tortoise for MySQL and return SQL statements."""
    try:
        with patch("aiomysql.create_pool", new=MagicMock()):
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
            return get_schema_sql(connections.get("default"), safe).split("; ")
    except ImportError:
        pytest.skip("aiomysql not installed")


@pytest.mark.asyncio
async def test_mysql_noid():
    await _reset_tortoise()
    try:
        sqls = await _init_for_mysql("tests.testmodels")
        sql = _get_sql(sqls, "`noid`")
        assert "`name` VARCHAR(255)" in sql
        assert "`id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT" in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_create_index():
    await _reset_tortoise()
    try:
        sqls = await _init_for_mysql("tests.testmodels")
        sql = _get_sql(sqls, "KEY")
        assert re.search(r"idx_tournament_created_\w+", sql) is not None
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_minrelation():
    await _reset_tortoise()
    try:
        sqls = await _init_for_mysql("tests.testmodels")
        sql = _get_sql(sqls, "`minrelation`")
        assert "`tournament_id` SMALLINT NOT NULL," in sql
        assert (
            "FOREIGN KEY (`tournament_id`) REFERENCES `tournament` (`id`) ON DELETE CASCADE" in sql
        )
        assert "participants" not in sql

        sql = _get_sql(sqls, "`minrelation_team`")
        assert "`minrelation_id` INT NOT NULL" in sql
        assert (
            "FOREIGN KEY (`minrelation_id`) REFERENCES `minrelation` (`id`) ON DELETE CASCADE"
            in sql
        )
        assert "`team_id` INT NOT NULL" in sql
        assert "FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE" in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_table_and_row_comment_generation():
    await _reset_tortoise()
    try:
        sqls = await _init_for_mysql("tests.testmodels")
        sql = _get_sql(sqls, "comments")
        assert "COMMENT='Test Table comment'" in sql
        assert "COMMENT 'This column acts as it\\'s own comment'" in sql
        assert re.search(r".*\\n.*", sql)
        assert re.search(r".*it\\'s.*", sql)
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_schema_no_db_constraint():
    await _reset_tortoise()
    try:
        await _init_for_mysql("tests.schema.models_no_db_constraint")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == r"""CREATE TABLE `team` (
    `name` VARCHAR(50) NOT NULL PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL COMMENT 'Created */\'`/* datetime',
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\'`/* we have';
CREATE TABLE `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL,
    `prize` DECIMAL(10,2),
    `token` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Unique token',
    `key` VARCHAR(100) NOT NULL,
    `tournament_id` SMALLINT NOT NULL COMMENT 'FK to tournament',
    UNIQUE KEY `uid_event_name_c6f89f` (`name`, `prize`),
    UNIQUE KEY `uid_event_tournam_a5b730` (`tournament_id`, `key`)
) CHARACTER SET utf8mb4 COMMENT='This table contains a list of all the events';
CREATE TABLE `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    UNIQUE KEY `uidx_team_team_team_re_d994df` (`team_rel_id`, `team_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE `teamevents` (
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    UNIQUE KEY `uidx_teamevents_event_i_664dbc` (`event_id`, `team_id`)
) CHARACTER SET utf8mb4 COMMENT='How participants relate';"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_schema():
    await _reset_tortoise()
    try:
        await _init_for_mysql("tests.schema.models_schema_create")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == """
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
    `name` VARCHAR(50) NOT NULL PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    CONSTRAINT `fk_team_team_9c77cd8f` FOREIGN KEY (`manager_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE `teamaddress` (
    `city` VARCHAR(50) NOT NULL COMMENT 'City',
    `country` VARCHAR(50) NOT NULL COMMENT 'Country',
    `street` VARCHAR(128) NOT NULL COMMENT 'Street Address',
    `team_id` VARCHAR(50) NOT NULL PRIMARY KEY,
    CONSTRAINT `fk_teamaddr_team_1c78d737` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='The Team\\'s address';
CREATE TABLE `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL COMMENT 'Created */\\'`/* datetime',
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\\'`/* we have';
CREATE TABLE `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL,
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
    `capacity` INT NOT NULL COMMENT 'No. of seats',
    `rent` DOUBLE NOT NULL,
    `team_id` VARCHAR(50) UNIQUE,
    CONSTRAINT `fk_venueinf_team_198af929` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE `sometable_self` (
    `backward_sts` INT NOT NULL,
    `sts_forward` INT NOT NULL,
    FOREIGN KEY (`backward_sts`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    FOREIGN KEY (`sts_forward`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_sometable_s_backwar_fc8fc8` (`backward_sts`, `sts_forward`)
) CHARACTER SET utf8mb4;
CREATE TABLE `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`team_rel_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_team_team_team_re_d994df` (`team_rel_id`, `team_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE `teamevents` (
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`event_id`) REFERENCES `event` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL,
    UNIQUE KEY `uidx_teamevents_event_i_664dbc` (`event_id`, `team_id`)
) CHARACTER SET utf8mb4 COMMENT='How participants relate';
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_schema_safe():
    await _reset_tortoise()
    try:
        await _init_for_mysql("tests.schema.models_schema_create")
        sql = get_schema_sql(connections.get("default"), safe=True).strip()
        if sql == SAFE_SCHEMA_SQL:
            # Sometimes github action get different result from local machine(Ubuntu20)
            assert sql == SAFE_SCHEMA_SQL
            return
        assert (
            sql
            == """
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
    `name` VARCHAR(50) NOT NULL PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    CONSTRAINT `fk_team_team_9c77cd8f` FOREIGN KEY (`manager_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE IF NOT EXISTS `teamaddress` (
    `city` VARCHAR(50) NOT NULL COMMENT 'City',
    `country` VARCHAR(50) NOT NULL COMMENT 'Country',
    `street` VARCHAR(128) NOT NULL COMMENT 'Street Address',
    `team_id` VARCHAR(50) NOT NULL PRIMARY KEY,
    CONSTRAINT `fk_teamaddr_team_1c78d737` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='The Team\\'s address';
CREATE TABLE IF NOT EXISTS `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL COMMENT 'Created */\\'`/* datetime',
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\\'`/* we have';
CREATE TABLE IF NOT EXISTS `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL,
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
    `capacity` INT NOT NULL COMMENT 'No. of seats',
    `rent` DOUBLE NOT NULL,
    `team_id` VARCHAR(50) UNIQUE,
    CONSTRAINT `fk_venueinf_team_198af929` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sometable_self` (
    `backward_sts` INT NOT NULL,
    `sts_forward` INT NOT NULL,
    FOREIGN KEY (`backward_sts`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    FOREIGN KEY (`sts_forward`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_sometable_s_backwar_fc8fc8` (`backward_sts`, `sts_forward`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`team_rel_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_team_team_team_re_d994df` (`team_rel_id`, `team_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `teamevents` (
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`event_id`) REFERENCES `event` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL,
    UNIQUE KEY `uidx_teamevents_event_i_664dbc` (`event_id`, `team_id`)
) CHARACTER SET utf8mb4 COMMENT='How participants relate';
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_index_safe():
    await _reset_tortoise()
    try:
        await _init_for_mysql("tests.schema.models_mysql_index")
        sql = get_schema_sql(connections.get("default"), safe=True)
        assert (
            sql
            == """CREATE TABLE IF NOT EXISTS `index` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `full_text` LONGTEXT NOT NULL,
    `geometry` GEOMETRY NOT NULL,
    FULLTEXT KEY `idx_index_full_te_3caba4` (`full_text`) WITH PARSER ngram,
    SPATIAL KEY `idx_index_geometr_0b4dfb` (`geometry`)
) CHARACTER SET utf8mb4;"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_index_unsafe():
    await _reset_tortoise()
    try:
        await _init_for_mysql("tests.schema.models_mysql_index")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql
            == """CREATE TABLE `index` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `full_text` LONGTEXT NOT NULL,
    `geometry` GEOMETRY NOT NULL,
    FULLTEXT KEY `idx_index_full_te_3caba4` (`full_text`) WITH PARSER ngram,
    SPATIAL KEY `idx_index_geometr_0b4dfb` (`geometry`)
) CHARACTER SET utf8mb4;"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_m2m_no_auto_create():
    await _reset_tortoise()
    try:
        await _init_for_mysql("tests.schema.models_no_auto_create_m2m")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == r"""CREATE TABLE `team` (
    `name` VARCHAR(50) NOT NULL PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    CONSTRAINT `fk_team_team_9c77cd8f` FOREIGN KEY (`manager_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL COMMENT 'Created */\'`/* datetime',
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\'`/* we have';
CREATE TABLE `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL,
    `prize` DECIMAL(10,2),
    `token` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Unique token',
    `key` VARCHAR(100) NOT NULL,
    `tournament_id` SMALLINT NOT NULL COMMENT 'FK to tournament',
    UNIQUE KEY `uid_event_name_c6f89f` (`name`, `prize`),
    UNIQUE KEY `uid_event_tournam_a5b730` (`tournament_id`, `key`),
    CONSTRAINT `fk_event_tourname_51c2b82d` FOREIGN KEY (`tournament_id`) REFERENCES `tournament` (`tid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='This table contains a list of all the events';
CREATE TABLE `teamevents` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `score` INT NOT NULL,
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    UNIQUE KEY `uid_teamevents_team_id_9e89fc` (`team_id`, `event_id`),
    CONSTRAINT `fk_teameven_event_9d3bac2d` FOREIGN KEY (`event_id`) REFERENCES `event` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_teameven_team_dc3bc201` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='How participants relate';
CREATE TABLE `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`team_rel_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_team_team_team_re_d994df` (`team_rel_id`, `team_id`)
) CHARACTER SET utf8mb4;
""".strip()
        )
    finally:
        await _teardown_tortoise()


# ============================================================================
# PostgreSQL Tests (asyncpg)
# ============================================================================


async def _init_for_asyncpg(module: str, safe: bool = False) -> list[str]:
    """Initialize Tortoise for asyncpg and return SQL statements."""
    try:
        with patch("asyncpg.create_pool", new=MagicMock()):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.asyncpg",
                            "credentials": {
                                "database": "test",
                                "host": "127.0.0.1",
                                "password": "foomip",
                                "port": 5432,
                                "user": "root",
                            },
                        }
                    },
                    "apps": {"models": {"models": [module], "default_connection": "default"}},
                }
            )
            return get_schema_sql(connections.get("default"), safe).split("; ")
    except ImportError:
        pytest.skip("asyncpg not installed")


@pytest.mark.asyncio
async def test_asyncpg_noid():
    await _reset_tortoise()
    try:
        sqls = await _init_for_asyncpg("tests.testmodels")
        sql = _get_sql(sqls, '"noid"')
        assert '"name" VARCHAR(255)' in sql
        assert '"id" SERIAL NOT NULL PRIMARY KEY' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_table_and_row_comment_generation():
    await _reset_tortoise()
    try:
        sqls = await _init_for_asyncpg("tests.testmodels")
        sql = _get_sql(sqls, "comments")
        assert "COMMENT ON TABLE \"comments\" IS 'Test Table comment'" in sql
        assert (
            'COMMENT ON COLUMN "comments"."escaped_comment_field" IS '
            "'This column acts as it''s own comment'" in sql
        )
        assert 'COMMENT ON COLUMN "comments"."multiline_comment" IS \'Some \\n comment\'' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_schema_no_db_constraint():
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_no_db_constraint")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == r"""CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL PRIMARY KEY,
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
    "created" TIMESTAMPTZ NOT NULL
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL,
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
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL,
    "team_id" VARCHAR(50) NOT NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
CREATE UNIQUE INDEX "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_schema():
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_schema_create")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == """
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
    "name" VARCHAR(50) NOT NULL PRIMARY KEY,
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
    "team_id" VARCHAR(50) NOT NULL PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "teamaddress"."city" IS 'City';
COMMENT ON COLUMN "teamaddress"."country" IS 'Country';
COMMENT ON COLUMN "teamaddress"."street" IS 'Street Address';
COMMENT ON TABLE "teamaddress" IS 'The Team''s address';
CREATE TABLE "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL,
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
    "team_id" VARCHAR(50) UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON COLUMN "venueinformation"."capacity" IS 'No. of seats';
CREATE TABLE "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_sometable_s_backwar_fc8fc8" ON "sometable_self" ("backward_sts", "sts_forward");
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
CREATE UNIQUE INDEX "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_schema_safe():
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_schema_create")
        sql = get_schema_sql(connections.get("default"), safe=True)
        assert (
            sql.strip()
            == """
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
    "name" VARCHAR(50) NOT NULL PRIMARY KEY,
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
    "team_id" VARCHAR(50) NOT NULL PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "teamaddress"."city" IS 'City';
COMMENT ON COLUMN "teamaddress"."country" IS 'Country';
COMMENT ON COLUMN "teamaddress"."street" IS 'Street Address';
COMMENT ON TABLE "teamaddress" IS 'The Team''s address';
CREATE TABLE IF NOT EXISTS "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE IF NOT EXISTS "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL,
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
    "team_id" VARCHAR(50) UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON COLUMN "venueinformation"."capacity" IS 'No. of seats';
CREATE TABLE IF NOT EXISTS "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_sometable_s_backwar_fc8fc8" ON "sometable_self" ("backward_sts", "sts_forward");
CREATE TABLE IF NOT EXISTS "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE IF NOT EXISTS "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_index_unsafe():
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_postgres_index")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql
            == """CREATE TABLE "index" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "bloom" VARCHAR(200) NOT NULL,
    "brin" VARCHAR(200) NOT NULL,
    "gin" TSVECTOR NOT NULL,
    "gist" TSVECTOR NOT NULL,
    "sp_gist" VARCHAR(200) NOT NULL,
    "hash" VARCHAR(200) NOT NULL,
    "partial" VARCHAR(200) NOT NULL,
    "title" TEXT NOT NULL,
    "body" TEXT NOT NULL
);
CREATE INDEX "idx_index_bloom_280137" ON "index" USING BLOOM ("bloom");
CREATE INDEX "idx_index_brin_a54a00" ON "index" USING BRIN ("brin");
CREATE INDEX "idx_index_gin_a403ee" ON "index" USING GIN ("gin");
CREATE INDEX "idx_index_gist_c807bf" ON "index" USING GIST ("gist");
CREATE INDEX "idx_index_sp_gist_2c0bad" ON "index" USING SPGIST ("sp_gist");
CREATE INDEX "idx_index_hash_cfe6b5" ON "index" USING HASH ("hash");
CREATE INDEX "idx_index_partial_c5be6a" ON "index" ("partial") WHERE id = 1;
CREATE INDEX "idx_index_(TO_TSV_50a2c7" ON "index" USING GIN ((TO_TSVECTOR('english',(("title" || ' ') || "body"))));"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_index_safe():
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_postgres_index")
        sql = get_schema_sql(connections.get("default"), safe=True)
        assert (
            sql
            == """CREATE TABLE IF NOT EXISTS "index" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "bloom" VARCHAR(200) NOT NULL,
    "brin" VARCHAR(200) NOT NULL,
    "gin" TSVECTOR NOT NULL,
    "gist" TSVECTOR NOT NULL,
    "sp_gist" VARCHAR(200) NOT NULL,
    "hash" VARCHAR(200) NOT NULL,
    "partial" VARCHAR(200) NOT NULL,
    "title" TEXT NOT NULL,
    "body" TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_index_bloom_280137" ON "index" USING BLOOM ("bloom");
CREATE INDEX IF NOT EXISTS "idx_index_brin_a54a00" ON "index" USING BRIN ("brin");
CREATE INDEX IF NOT EXISTS "idx_index_gin_a403ee" ON "index" USING GIN ("gin");
CREATE INDEX IF NOT EXISTS "idx_index_gist_c807bf" ON "index" USING GIST ("gist");
CREATE INDEX IF NOT EXISTS "idx_index_sp_gist_2c0bad" ON "index" USING SPGIST ("sp_gist");
CREATE INDEX IF NOT EXISTS "idx_index_hash_cfe6b5" ON "index" USING HASH ("hash");
CREATE INDEX IF NOT EXISTS "idx_index_partial_c5be6a" ON "index" ("partial") WHERE id = 1;
CREATE INDEX IF NOT EXISTS "idx_index_(TO_TSV_50a2c7" ON "index" USING GIN ((TO_TSVECTOR('english',(("title" || ' ') || "body"))));"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_m2m_no_auto_create():
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_no_auto_create_m2m")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == r"""CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL PRIMARY KEY,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
COMMENT ON COLUMN "team"."name" IS 'The TEAM name (and PK)';
COMMENT ON TABLE "team" IS 'The TEAMS!';
CREATE TABLE "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL,
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
CREATE TABLE "teamevents" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "score" INT NOT NULL,
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    CONSTRAINT "uid_teamevents_team_id_9e89fc" UNIQUE ("team_id", "event_id")
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_pgfields_unsafe():
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_postgres_fields")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql
            == """CREATE TABLE "postgres_fields" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tsvector" TSVECTOR NOT NULL,
    "text_array" TEXT[] NOT NULL,
    "varchar_array" VARCHAR(32)[] NOT NULL,
    "int_array" INT[],
    "real_array" REAL[] NOT NULL
);
COMMENT ON COLUMN "postgres_fields"."real_array" IS 'this is array of real numbers';"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_pgfields_safe():
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_postgres_fields")
        sql = get_schema_sql(connections.get("default"), safe=True)
        assert (
            sql
            == """CREATE TABLE IF NOT EXISTS "postgres_fields" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tsvector" TSVECTOR NOT NULL,
    "text_array" TEXT[] NOT NULL,
    "varchar_array" VARCHAR(32)[] NOT NULL,
    "int_array" INT[],
    "real_array" REAL[] NOT NULL
);
COMMENT ON COLUMN "postgres_fields"."real_array" IS 'this is array of real numbers';"""
        )
    finally:
        await _teardown_tortoise()


# ============================================================================
# PostgreSQL Tests (psycopg)
# ============================================================================


async def _init_for_psycopg(module: str, safe: bool = False) -> list[str]:
    """Initialize Tortoise for psycopg and return SQL statements."""
    try:
        with patch("psycopg_pool.AsyncConnectionPool.open", new=MagicMock()):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.psycopg",
                            "credentials": {
                                "database": "test",
                                "host": "127.0.0.1",
                                "password": "foomip",
                                "port": 5432,
                                "user": "root",
                            },
                        }
                    },
                    "apps": {"models": {"models": [module], "default_connection": "default"}},
                }
            )
            return get_schema_sql(connections.get("default"), safe).split("; ")
    except ImportError:
        pytest.skip("psycopg not installed")


@pytest.mark.asyncio
async def test_psycopg_noid():
    await _reset_tortoise()
    try:
        sqls = await _init_for_psycopg("tests.testmodels")
        sql = _get_sql(sqls, '"noid"')
        assert '"name" VARCHAR(255)' in sql
        assert '"id" SERIAL NOT NULL PRIMARY KEY' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_table_and_row_comment_generation():
    await _reset_tortoise()
    try:
        sqls = await _init_for_psycopg("tests.testmodels")
        sql = _get_sql(sqls, "comments")
        assert "COMMENT ON TABLE \"comments\" IS 'Test Table comment'" in sql
        assert (
            'COMMENT ON COLUMN "comments"."escaped_comment_field" IS '
            "'This column acts as it''s own comment'" in sql
        )
        assert 'COMMENT ON COLUMN "comments"."multiline_comment" IS \'Some \\n comment\'' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_schema_no_db_constraint():
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_no_db_constraint")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == r"""CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL PRIMARY KEY,
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
    "created" TIMESTAMPTZ NOT NULL
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL,
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
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL,
    "team_id" VARCHAR(50) NOT NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
CREATE UNIQUE INDEX "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_schema():
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_schema_create")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == """
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
    "name" VARCHAR(50) NOT NULL PRIMARY KEY,
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
    "team_id" VARCHAR(50) NOT NULL PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "teamaddress"."city" IS 'City';
COMMENT ON COLUMN "teamaddress"."country" IS 'Country';
COMMENT ON COLUMN "teamaddress"."street" IS 'Street Address';
COMMENT ON TABLE "teamaddress" IS 'The Team''s address';
CREATE TABLE "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL,
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
    "team_id" VARCHAR(50) UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON COLUMN "venueinformation"."capacity" IS 'No. of seats';
CREATE TABLE "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_sometable_s_backwar_fc8fc8" ON "sometable_self" ("backward_sts", "sts_forward");
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
CREATE UNIQUE INDEX "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_schema_safe():
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_schema_create")
        sql = get_schema_sql(connections.get("default"), safe=True)
        assert (
            sql.strip()
            == """
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
    "name" VARCHAR(50) NOT NULL PRIMARY KEY,
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
    "team_id" VARCHAR(50) NOT NULL PRIMARY KEY REFERENCES "team" ("name") ON DELETE CASCADE
);
COMMENT ON COLUMN "teamaddress"."city" IS 'City';
COMMENT ON COLUMN "teamaddress"."country" IS 'Country';
COMMENT ON COLUMN "teamaddress"."street" IS 'Street Address';
COMMENT ON TABLE "teamaddress" IS 'The Team''s address';
CREATE TABLE IF NOT EXISTS "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE IF NOT EXISTS "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL,
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
    "team_id" VARCHAR(50) UNIQUE REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON COLUMN "venueinformation"."capacity" IS 'No. of seats';
CREATE TABLE IF NOT EXISTS "sometable_self" (
    "backward_sts" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE,
    "sts_forward" INT NOT NULL REFERENCES "sometable" ("sometable_id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_sometable_s_backwar_fc8fc8" ON "sometable_self" ("backward_sts", "sts_forward");
CREATE TABLE IF NOT EXISTS "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
CREATE TABLE IF NOT EXISTS "teamevents" (
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE SET NULL,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE SET NULL
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_teamevents_event_i_664dbc" ON "teamevents" ("event_id", "team_id");
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_index_unsafe():
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_postgres_index")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql
            == """CREATE TABLE "index" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "bloom" VARCHAR(200) NOT NULL,
    "brin" VARCHAR(200) NOT NULL,
    "gin" TSVECTOR NOT NULL,
    "gist" TSVECTOR NOT NULL,
    "sp_gist" VARCHAR(200) NOT NULL,
    "hash" VARCHAR(200) NOT NULL,
    "partial" VARCHAR(200) NOT NULL,
    "title" TEXT NOT NULL,
    "body" TEXT NOT NULL
);
CREATE INDEX "idx_index_bloom_280137" ON "index" USING BLOOM ("bloom");
CREATE INDEX "idx_index_brin_a54a00" ON "index" USING BRIN ("brin");
CREATE INDEX "idx_index_gin_a403ee" ON "index" USING GIN ("gin");
CREATE INDEX "idx_index_gist_c807bf" ON "index" USING GIST ("gist");
CREATE INDEX "idx_index_sp_gist_2c0bad" ON "index" USING SPGIST ("sp_gist");
CREATE INDEX "idx_index_hash_cfe6b5" ON "index" USING HASH ("hash");
CREATE INDEX "idx_index_partial_c5be6a" ON "index" ("partial") WHERE id = 1;
CREATE INDEX "idx_index_(TO_TSV_50a2c7" ON "index" USING GIN ((TO_TSVECTOR('english',(("title" || ' ') || "body"))));"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_index_safe():
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_postgres_index")
        sql = get_schema_sql(connections.get("default"), safe=True)
        assert (
            sql
            == """CREATE TABLE IF NOT EXISTS "index" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "bloom" VARCHAR(200) NOT NULL,
    "brin" VARCHAR(200) NOT NULL,
    "gin" TSVECTOR NOT NULL,
    "gist" TSVECTOR NOT NULL,
    "sp_gist" VARCHAR(200) NOT NULL,
    "hash" VARCHAR(200) NOT NULL,
    "partial" VARCHAR(200) NOT NULL,
    "title" TEXT NOT NULL,
    "body" TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_index_bloom_280137" ON "index" USING BLOOM ("bloom");
CREATE INDEX IF NOT EXISTS "idx_index_brin_a54a00" ON "index" USING BRIN ("brin");
CREATE INDEX IF NOT EXISTS "idx_index_gin_a403ee" ON "index" USING GIN ("gin");
CREATE INDEX IF NOT EXISTS "idx_index_gist_c807bf" ON "index" USING GIST ("gist");
CREATE INDEX IF NOT EXISTS "idx_index_sp_gist_2c0bad" ON "index" USING SPGIST ("sp_gist");
CREATE INDEX IF NOT EXISTS "idx_index_hash_cfe6b5" ON "index" USING HASH ("hash");
CREATE INDEX IF NOT EXISTS "idx_index_partial_c5be6a" ON "index" ("partial") WHERE id = 1;
CREATE INDEX IF NOT EXISTS "idx_index_(TO_TSV_50a2c7" ON "index" USING GIN ((TO_TSVECTOR('english',(("title" || ' ') || "body"))));"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_m2m_no_auto_create():
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_no_auto_create_m2m")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql.strip()
            == r"""CREATE TABLE "team" (
    "name" VARCHAR(50) NOT NULL PRIMARY KEY,
    "key" INT NOT NULL,
    "manager_id" VARCHAR(50) REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE INDEX "idx_team_manager_676134" ON "team" ("manager_id", "key");
CREATE INDEX "idx_team_manager_ef8f69" ON "team" ("manager_id", "name");
COMMENT ON COLUMN "team"."name" IS 'The TEAM name (and PK)';
COMMENT ON TABLE "team" IS 'The TEAMS!';
CREATE TABLE "tournament" (
    "tid" SMALLSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "created" TIMESTAMPTZ NOT NULL
);
CREATE INDEX "idx_tournament_name_6fe200" ON "tournament" ("name");
COMMENT ON COLUMN "tournament"."name" IS 'Tournament name';
COMMENT ON COLUMN "tournament"."created" IS 'Created */''`/* datetime';
COMMENT ON TABLE "tournament" IS 'What Tournaments */''`/* we have';
CREATE TABLE "event" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "modified" TIMESTAMPTZ NOT NULL,
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
CREATE TABLE "teamevents" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "score" INT NOT NULL,
    "event_id" BIGINT NOT NULL REFERENCES "event" ("id") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    CONSTRAINT "uid_teamevents_team_id_9e89fc" UNIQUE ("team_id", "event_id")
);
COMMENT ON TABLE "teamevents" IS 'How participants relate';
CREATE TABLE "team_team" (
    "team_rel_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE,
    "team_id" VARCHAR(50) NOT NULL REFERENCES "team" ("name") ON DELETE CASCADE
);
CREATE UNIQUE INDEX "uidx_team_team_team_re_d994df" ON "team_team" ("team_rel_id", "team_id");
""".strip()
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_pgfields_unsafe():
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_postgres_fields")
        sql = get_schema_sql(connections.get("default"), safe=False)
        assert (
            sql
            == """CREATE TABLE "postgres_fields" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tsvector" TSVECTOR NOT NULL,
    "text_array" TEXT[] NOT NULL,
    "varchar_array" VARCHAR(32)[] NOT NULL,
    "int_array" INT[],
    "real_array" REAL[] NOT NULL
);
COMMENT ON COLUMN "postgres_fields"."real_array" IS 'this is array of real numbers';"""
        )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_pgfields_safe():
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_postgres_fields")
        sql = get_schema_sql(connections.get("default"), safe=True)
        assert (
            sql
            == """CREATE TABLE IF NOT EXISTS "postgres_fields" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "tsvector" TSVECTOR NOT NULL,
    "text_array" TEXT[] NOT NULL,
    "varchar_array" VARCHAR(32)[] NOT NULL,
    "int_array" INT[],
    "real_array" REAL[] NOT NULL
);
COMMENT ON COLUMN "postgres_fields"."real_array" IS 'this is array of real numbers';"""
        )
    finally:
        await _teardown_tortoise()


# ============================================================================
# Schema-Qualified Table Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sqlite_schema_qualified_ignores_schema():
    """SQLite should ignore Meta.schema and produce standard table names."""
    await _reset_tortoise()
    try:
        sqls = await _init_for_sqlite("tests.schema.models_schema_qualified", safe=True)
        sql = " ".join(sqls)
        # SQLite should NOT have schema-qualified names
        assert '"custom"."category"' not in sql
        # Should have regular quoted table names
        assert '"category"' in sql
        assert '"product"' in sql
        assert '"tag"' in sql
        assert "CREATE SCHEMA" not in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_asyncpg_schema_qualified_safe():
    """Postgres (asyncpg) should produce schema-qualified names with CREATE SCHEMA."""
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_schema_qualified")
        sql = get_schema_sql(connections.get("default"), safe=True)
        # Should have CREATE SCHEMA
        assert 'CREATE SCHEMA IF NOT EXISTS "custom";' in sql
        # Should have schema-qualified CREATE TABLE
        assert 'CREATE TABLE IF NOT EXISTS "custom"."category"' in sql
        assert 'CREATE TABLE IF NOT EXISTS "custom"."product"' in sql
        assert 'CREATE TABLE IF NOT EXISTS "custom"."tag"' in sql
        # FK should reference schema-qualified table
        assert 'REFERENCES "custom"."category"' in sql
        # M2M through table should be schema-qualified
        assert 'CREATE TABLE IF NOT EXISTS "custom"."product_tags"' in sql
        # M2M FK references should be schema-qualified
        assert 'REFERENCES "custom"."product"' in sql
        assert 'REFERENCES "custom"."tag"' in sql
        # Comments should use schema-qualified table
        assert 'COMMENT ON COLUMN "custom"."category"."name" IS \'Category name\'' in sql
        assert 'COMMENT ON TABLE "custom"."product" IS \'Products table\'' in sql
        # Unique index on M2M through table should use schema-qualified table
        assert 'ON "custom"."product_tags"' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_schema_qualified_safe():
    """Postgres (psycopg) should produce schema-qualified names with CREATE SCHEMA."""
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_schema_qualified")
        sql = get_schema_sql(connections.get("default"), safe=True)
        # Should have CREATE SCHEMA
        assert 'CREATE SCHEMA IF NOT EXISTS "custom";' in sql
        # Should have schema-qualified CREATE TABLE
        assert 'CREATE TABLE IF NOT EXISTS "custom"."category"' in sql
        assert 'CREATE TABLE IF NOT EXISTS "custom"."product"' in sql
        assert 'CREATE TABLE IF NOT EXISTS "custom"."tag"' in sql
        # FK should reference schema-qualified table
        assert 'REFERENCES "custom"."category"' in sql
        # M2M through table should be schema-qualified
        assert 'CREATE TABLE IF NOT EXISTS "custom"."product_tags"' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_psycopg_schema_qualified_unsafe():
    """Postgres (psycopg) unsafe should produce CREATE SCHEMA without IF NOT EXISTS."""
    await _reset_tortoise()
    try:
        await _init_for_psycopg("tests.schema.models_schema_qualified")
        sql = get_schema_sql(connections.get("default"), safe=False)
        # Should have CREATE SCHEMA without IF NOT EXISTS
        assert 'CREATE SCHEMA "custom";' in sql
        assert "IF NOT EXISTS" not in sql.split("CREATE TABLE")[0].replace(
            'CREATE SCHEMA "custom";', ""
        )
        # Should have schema-qualified CREATE TABLE
        assert 'CREATE TABLE "custom"."category"' in sql
        assert 'CREATE TABLE "custom"."product"' in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_mysql_schema_qualified():
    """MySQL should produce schema-qualified names with backtick quoting."""
    await _reset_tortoise()
    try:
        sqls = await _init_for_mysql("tests.schema.models_schema_qualified", safe=True)
        sql = " ".join(sqls)
        # MySQL should have backtick-qualified names
        assert "`custom`.`category`" in sql
        assert "`custom`.`product`" in sql
        assert "`custom`.`tag`" in sql
        # FK should reference qualified table
        assert "REFERENCES `custom`.`category`" in sql
        # M2M through table should be qualified
        assert "`custom`.`product_tags`" in sql
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_schema_qualified_single_schema_creation():
    """Only one CREATE SCHEMA per unique schema value."""
    await _reset_tortoise()
    try:
        await _init_for_asyncpg("tests.schema.models_schema_qualified")
        sql = get_schema_sql(connections.get("default"), safe=True)
        # All 3 models share schema "custom" — should create only once
        assert sql.count('CREATE SCHEMA IF NOT EXISTS "custom"') == 1
    finally:
        await _teardown_tortoise()
