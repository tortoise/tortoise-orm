import sys
from pathlib import Path

import pytest

from tortoise import Tortoise
from tortoise.config import AppConfig, ConnectionConfig, TortoiseConfig
from tortoise.migrations.api import migrate, plan, sqlmigrate


def _setup_multi_connection_projects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> TortoiseConfig:
    for mod in list(sys.modules):
        if mod.startswith("app_c"):
            sys.modules.pop(mod, None)

    _setup_cross_app_projects(tmp_path, monkeypatch)

    app_c_dir = tmp_path / "app_c"
    app_c_migrations = app_c_dir / "migrations"
    app_c_migrations.mkdir(parents=True)
    (app_c_dir / "__init__.py").write_text("", encoding="ascii")
    (app_c_migrations / "__init__.py").write_text("", encoding="ascii")
    (app_c_dir / "models.py").write_text(
        "\n".join(
            [
                "from tortoise import fields",
                "from tortoise.models import Model",
                "",
                "class Item(Model):",
                "    id = fields.IntField(pk=True)",
                "",
            ]
        ),
        encoding="ascii",
    )
    (app_c_migrations / "0001_initial.py").write_text(
        "\n".join(
            [
                "from tortoise import fields, migrations",
                "from tortoise.migrations import operations as ops",
                "",
                "class Migration(migrations.Migration):",
                "    dependencies = []",
                "    operations = [",
                "        ops.CreateModel(",
                "            name='Item',",
                "            fields=[",
                "                ('id', fields.IntField(pk=True)),",
                "            ],",
                "        ),",
                "    ]",
                "",
            ]
        ),
        encoding="ascii",
    )

    return TortoiseConfig(
        connections={
            "default": ConnectionConfig(
                engine="tortoise.backends.sqlite",
                credentials={"file_path": ":memory:"},
            ),
            "secondary": ConnectionConfig(
                engine="tortoise.backends.sqlite",
                credentials={"file_path": ":memory:"},
            ),
        },
        apps={
            "app_a": AppConfig(
                models=["app_a.models"],
                default_connection="default",
                migrations="app_a.migrations",
            ),
            "app_b": AppConfig(
                models=["app_b.models"],
                default_connection="default",
                migrations="app_b.migrations",
            ),
            "app_c": AppConfig(
                models=["app_c.models"],
                default_connection="secondary",
                migrations="app_c.migrations",
            ),
        },
    )


@pytest.mark.asyncio
async def test_plan_cross_app_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _setup_cross_app_projects(tmp_path, monkeypatch)

    try:
        output = await plan(config=config, app_labels=["app_b"])
        app_a_idx = next(i for i, line in enumerate(output) if "app_a.0001_initial" in line)
        app_b_idx = next(i for i, line in enumerate(output) if "app_b.0001_initial" in line)
        assert app_a_idx < app_b_idx
    finally:
        await Tortoise.close_connections()
        await Tortoise._reset_apps()
        for mod in list(sys.modules):
            if mod.startswith(("app_a", "app_b")):
                sys.modules.pop(mod, None)


@pytest.mark.asyncio
async def test_migrate_multi_connection_empty_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _setup_multi_connection_projects(tmp_path, monkeypatch)

    try:
        await migrate(config=config, app_labels=["app_b"])
        conn = Tortoise.get_connection("default")
        _, table_info = await conn.execute_query("PRAGMA table_info('concretemodel')")
        col_names = [row["name"] for row in table_info]
        assert "user_id" in col_names

        _, fk_info = await conn.execute_query("PRAGMA foreign_key_list('concretemodel')")
        assert any(row["table"] == "user" and row["from"] == "user_id" for row in fk_info)

        sec_conn = Tortoise.get_connection("secondary")
        _, sec_tables = await sec_conn.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='item'"
        )
        assert len(sec_tables) == 0
    finally:
        await Tortoise.close_connections()
        await Tortoise._reset_apps()
        for mod in list(sys.modules):
            if mod.startswith(("app_a", "app_b", "app_c")):
                sys.modules.pop(mod, None)


@pytest.mark.asyncio
async def test_plan_multi_connection_empty_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _setup_multi_connection_projects(tmp_path, monkeypatch)

    try:
        output = await plan(config=config, app_labels=["app_b"])
        app_a_idx = next(i for i, line in enumerate(output) if "app_a.0001_initial" in line)
        app_b_idx = next(i for i, line in enumerate(output) if "app_b.0001_initial" in line)
        assert app_a_idx < app_b_idx
        assert not any("app_c" in line for line in output)
        assert not any("secondary" in line for line in output)
    finally:
        await Tortoise.close_connections()
        await Tortoise._reset_apps()
        for mod in list(sys.modules):
            if mod.startswith(("app_a", "app_b", "app_c")):
                sys.modules.pop(mod, None)


@pytest.mark.asyncio
async def test_migrate_accepts_dataclass_config() -> None:
    config = TortoiseConfig(
        connections={
            "default": ConnectionConfig(
                engine="tortoise.backends.sqlite",
                credentials={"file_path": ":memory:"},
            )
        },
        apps={"models": AppConfig(models=["tests.testmodels"], default_connection="default")},
    )
    try:
        await migrate(config=config)
    finally:
        await Tortoise.close_connections()


def _setup_cross_app_projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TortoiseConfig:
    for mod in list(sys.modules):
        if mod.startswith(("app_a", "app_b")):
            sys.modules.pop(mod, None)

    app_a_dir = tmp_path / "app_a"
    app_a_migrations = app_a_dir / "migrations"
    app_a_migrations.mkdir(parents=True)
    (app_a_dir / "__init__.py").write_text("", encoding="ascii")
    (app_a_migrations / "__init__.py").write_text("", encoding="ascii")
    (app_a_dir / "models.py").write_text(
        "\n".join(
            [
                "from tortoise import fields",
                "from tortoise.models import Model",
                "",
                "class User(Model):",
                "    id = fields.IntField(pk=True)",
                "    username = fields.CharField(max_length=50)",
                "",
            ]
        ),
        encoding="ascii",
    )
    (app_a_migrations / "0001_initial.py").write_text(
        "\n".join(
            [
                "from tortoise import fields, migrations",
                "from tortoise.migrations import operations as ops",
                "",
                "class Migration(migrations.Migration):",
                "    dependencies = []",
                "    operations = [",
                "        ops.CreateModel(",
                "            name='User',",
                "            fields=[",
                "                ('id', fields.IntField(pk=True)),",
                "                ('username', fields.CharField(max_length=50)),",
                "            ],",
                "        ),",
                "    ]",
                "",
            ]
        ),
        encoding="ascii",
    )

    app_b_dir = tmp_path / "app_b"
    app_b_migrations = app_b_dir / "migrations"
    app_b_migrations.mkdir(parents=True)
    (app_b_dir / "__init__.py").write_text("", encoding="ascii")
    (app_b_migrations / "__init__.py").write_text("", encoding="ascii")
    (app_b_dir / "models.py").write_text(
        "\n".join(
            [
                "from tortoise import fields",
                "from tortoise.models import Model",
                "",
                "class GenericModel(Model):",
                "    user = fields.ForeignKeyField('app_a.User')",
                "",
                "    class Meta:",
                "        abstract = True",
                "",
                "class ModelA(GenericModel):",
                "    class Meta:",
                "        abstract = True",
                "",
                "class ModelB(ModelA):",
                "    class Meta:",
                "        abstract = True",
                "",
                "class ConcreteModel(ModelB):",
                "    id = fields.IntField(pk=True)",
                "",
            ]
        ),
        encoding="ascii",
    )
    (app_b_migrations / "0001_initial.py").write_text(
        "\n".join(
            [
                "from tortoise import fields, migrations",
                "from tortoise.migrations import operations as ops",
                "",
                "class Migration(migrations.Migration):",
                "    dependencies = [('app_a', '0001_initial')]",
                "    operations = [",
                "        ops.CreateModel(",
                "            name='ConcreteModel',",
                "            fields=[",
                "                ('id', fields.IntField(pk=True)),",
                "                ('user', fields.ForeignKeyField('app_a.User')),",
                "            ],",
                "        ),",
                "    ]",
                "",
            ]
        ),
        encoding="ascii",
    )

    monkeypatch.syspath_prepend(str(tmp_path))

    return TortoiseConfig(
        connections={
            "default": ConnectionConfig(
                engine="tortoise.backends.sqlite",
                credentials={"file_path": ":memory:"},
            )
        },
        apps={
            "app_a": AppConfig(
                models=["app_a.models"],
                default_connection="default",
                migrations="app_a.migrations",
            ),
            "app_b": AppConfig(
                models=["app_b.models"],
                default_connection="default",
                migrations="app_b.migrations",
            ),
        },
    )


@pytest.mark.asyncio
async def test_sqlmigrate_cross_app_foreign_key_in_table_sql(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _setup_cross_app_projects(tmp_path, monkeypatch)

    try:
        sql_statements = await sqlmigrate(
            config=config,
            app_label="app_b",
            migration_name="0001_initial",
        )
        combined_sql = "\n".join(sql_statements)
        assert '"user_id"' in combined_sql or "user_id" in combined_sql
        assert 'REFERENCES "user"' in combined_sql or "REFERENCES user" in combined_sql
    finally:
        await Tortoise.close_connections()
        await Tortoise._reset_apps()
        for mod in list(sys.modules):
            if mod.startswith(("app_a", "app_b")):
                sys.modules.pop(mod, None)


@pytest.mark.asyncio
async def test_migrate_cross_app_foreign_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _setup_cross_app_projects(tmp_path, monkeypatch)

    try:
        await migrate(config=config, app_labels=["app_b"])
        conn = Tortoise.get_connection("default")
        _, table_info = await conn.execute_query("PRAGMA table_info('concretemodel')")
        col_names = [row["name"] for row in table_info]
        assert "user_id" in col_names

        _, fk_info = await conn.execute_query("PRAGMA foreign_key_list('concretemodel')")
        assert any(row["table"] == "user" and row["from"] == "user_id" for row in fk_info)
    finally:
        await Tortoise.close_connections()
        await Tortoise._reset_apps()
        for mod in list(sys.modules):
            if mod.startswith(("app_a", "app_b")):
                sys.modules.pop(mod, None)
