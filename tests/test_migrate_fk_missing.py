import datetime as dt
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tortoise import Tortoise, fields, models
from tortoise.migrations.api import sqlmigrate
from tortoise.migrations.autodetector import MigrationAutodetector


class DummyUser(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)

    class Meta:
        app = "app_a"


class DummyAbstractBase(models.Model):
    user = fields.ForeignKeyField("app_a.DummyUser", related_name="bases")

    class Meta:
        abstract = True
        app = "app_b"


class DummyConcrete(DummyAbstractBase):
    data = fields.CharField(max_length=50)

    class Meta:
        app = "app_b"


@pytest.mark.asyncio
async def test_fk_missing_in_sqlmigrate(tmp_path: Path):
    mod_a = ModuleType("test_mod_a")
    mod_a.DummyUser = DummyUser
    sys.modules["test_mod_a"] = mod_a

    mod_b = ModuleType("test_mod_b")
    mod_b.DummyAbstractBase = DummyAbstractBase
    mod_b.DummyConcrete = DummyConcrete
    sys.modules["test_mod_b"] = mod_b

    app_a_package = tmp_path / "app_a"
    app_a_migrations = app_a_package / "migrations"
    app_a_migrations.mkdir(parents=True, exist_ok=True)
    (app_a_package / "__init__.py").write_text("", encoding="ascii")
    (app_a_migrations / "__init__.py").write_text("", encoding="ascii")

    app_b_package = tmp_path / "app_b"
    app_b_migrations = app_b_package / "migrations"
    app_b_migrations.mkdir(parents=True, exist_ok=True)
    (app_b_package / "__init__.py").write_text("", encoding="ascii")
    (app_b_migrations / "__init__.py").write_text("", encoding="ascii")

    sys.path.insert(0, str(tmp_path))

    config = {
        "connections": {"default": "sqlite://:memory:"},
        "apps": {
            "app_a": {
                "models": ["test_mod_a"],
                "default_connection": "default",
                "migrations": "app_a.migrations",
            },
            "app_b": {
                "models": ["test_mod_b"],
                "default_connection": "default",
                "migrations": "app_b.migrations",
            },
        },
    }

    try:
        await Tortoise.init(config=config, init_connections=False)

        autodetector = MigrationAutodetector(
            Tortoise.apps,
            config["apps"],
            now=lambda: dt.datetime(2024, 1, 1, 12, 0),
        )
        changes = await autodetector.changes()
        for writer in changes:
            writer.write()

        await Tortoise.close_connections()

        migration_name = next(w.name for w in changes if w.app_label == "app_b")
        sql = await sqlmigrate(config=config, app_label="app_b", migration_name=migration_name)

        sql_joined = "\n".join(sql).lower()
        assert "references" in sql_joined, f"Foreign key missing in SQL: {sql_joined}"

    finally:
        sys.modules.pop("test_mod_a", None)
        sys.modules.pop("test_mod_b", None)
        sys.path.pop(0)
