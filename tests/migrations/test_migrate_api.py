import sys
from pathlib import Path
from typing import Any

import pytest

from tortoise import Tortoise
from tortoise.config import AppConfig, ConnectionConfig, TortoiseConfig
from tortoise.migrations.api import migrate, plan, sqlmigrate
from tortoise.migrations.executor import MigrationExecutor, MigrationTarget


def _cleanup_modules(*app_names: str) -> None:
    for mod in list(sys.modules):
        if any(mod == app or mod.startswith(f"{app}.") for app in app_names):
            sys.modules.pop(mod, None)


def _create_app_package(app_dir: Path, models_code: str, migration_code: str) -> None:
    migrations_dir = app_dir / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "__init__.py").write_text("", encoding="ascii")
    (migrations_dir / "__init__.py").write_text("", encoding="ascii")
    (app_dir / "models.py").write_text(models_code, encoding="ascii")
    (migrations_dir / "0001_initial.py").write_text(migration_code, encoding="ascii")


def _setup_multi_connection_projects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> TortoiseConfig:
    _cleanup_modules("app_c")

    _setup_cross_app_projects(tmp_path, monkeypatch)

    _create_app_package(
        tmp_path / "app_c",
        models_code="\n".join(
            [
                "from tortoise import fields",
                "from tortoise.models import Model",
                "",
                "class Item(Model):",
                "    id = fields.IntField(pk=True)",
                "",
            ]
        ),
        migration_code="\n".join(
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
        _cleanup_modules("app_a", "app_b")


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
        _cleanup_modules("app_a", "app_b", "app_c")


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
        _cleanup_modules("app_a", "app_b", "app_c")


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
    _cleanup_modules("app_a", "app_b")

    _create_app_package(
        tmp_path / "app_a",
        models_code="\n".join(
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
        migration_code="\n".join(
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
    )

    _create_app_package(
        tmp_path / "app_b",
        models_code="\n".join(
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
        migration_code="\n".join(
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
        _cleanup_modules("app_a", "app_b")


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
        _cleanup_modules("app_a", "app_b")


@pytest.mark.asyncio
async def test_migrate_multi_connection_target_exclusion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _setup_multi_connection_projects(tmp_path, monkeypatch)
    recorded_targets: dict[str, list[str]] = {}
    orig_migrate = MigrationExecutor.migrate

    async def mock_migrate(
        self: MigrationExecutor, targets: list[MigrationTarget], **kwargs: Any
    ) -> None:
        conn_name = next(
            k for k in config.connections if Tortoise.get_connection(k) == self.connection
        )
        recorded_targets[conn_name] = [t.app_label for t in targets]
        return await orig_migrate(self, targets, **kwargs)

    monkeypatch.setattr(MigrationExecutor, "migrate", mock_migrate)
    try:
        await migrate(config=config, app_labels=["app_b", "app_c"])
        assert "app_c" not in recorded_targets["default"]
        assert "app_b" in recorded_targets["default"]
        assert "app_a" not in recorded_targets["default"]
        assert "app_b" not in recorded_targets["secondary"]
        assert "app_a" not in recorded_targets["secondary"]
        assert "app_c" in recorded_targets["secondary"]
    finally:
        await Tortoise.close_connections()
        await Tortoise._reset_apps()
        _cleanup_modules("app_a", "app_b", "app_c")
