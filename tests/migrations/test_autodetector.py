from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest

from tortoise import fields
from tortoise.fields.base import Field
from tortoise.migrations.autodetector import MigrationAutodetector
from tortoise.migrations.operations import CreateModel, RenameField, RenameModel
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


def _prepare_migration_package(tmp_path: Path, app_label: str) -> str:
    package_dir = tmp_path / app_label
    migrations_dir = package_dir / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "__init__.py").write_text("", encoding="ascii")
    (migrations_dir / "__init__.py").write_text("", encoding="ascii")
    return f"{app_label}.migrations"


def _write_migration(
    tmp_path: Path,
    app_label: str,
    name: str,
    dependencies: list[tuple[str, str]] | None = None,
) -> str:
    module_path = _prepare_migration_package(tmp_path, app_label)
    migrations_dir = tmp_path / app_label / "migrations"
    content = [
        "from tortoise import migrations",
        "",
        "class Migration(migrations.Migration):",
        f"    dependencies = {dependencies or []!r}",
        "",
        "    operations = []",
        "",
    ]
    (migrations_dir / f"{name}.py").write_text("\n".join(content), encoding="ascii")
    return module_path


def _write_migration_with_ops(
    tmp_path: Path,
    app_label: str,
    name: str,
    operations_source: list[str],
    dependencies: list[tuple[str, str]] | None = None,
) -> str:
    module_path = _prepare_migration_package(tmp_path, app_label)
    migrations_dir = tmp_path / app_label / "migrations"
    content = [
        "from tortoise import migrations",
        "from tortoise.migrations import operations as ops",
        "from tortoise import fields",
        "",
        "class Migration(migrations.Migration):",
        f"    dependencies = {dependencies or []!r}",
        "",
        "    operations = [",
        *operations_source,
        "    ]",
        "",
    ]
    (migrations_dir / f"{name}.py").write_text("\n".join(content), encoding="ascii")
    return module_path


def _make_model(name: str, app_label: str, **model_fields: Field) -> type[Model]:
    attrs: dict[str, Any] = dict(model_fields)
    meta = type("Meta", (), {"app": app_label, "table": name.lower()})
    attrs["Meta"] = meta
    return type(name, (Model,), attrs)


@pytest.mark.asyncio
async def test_autodetector_initial_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = _prepare_migration_package(tmp_path, "autoapp_init")
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    Widget = _make_model("Widget", "autoapp_init", id=fields.IntField(pk=True))
    apps.register_model("autoapp_init", Widget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "autoapp_init": {
                "models": [],
                "default_connection": "default",
                "migrations": module_path,
            }
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    assert len(changes) == 1
    writer = changes[0]
    assert writer.name == "0001_initial"
    assert writer.initial is True
    assert any(isinstance(op, CreateModel) for op in writer.operations)


@pytest.mark.asyncio
async def test_autodetector_uses_latest_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = _write_migration(tmp_path, "autoapp_dep", "0001_initial")
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    Widget = _make_model("Widget", "autoapp_dep", id=fields.IntField(pk=True))
    apps.register_model("autoapp_dep", Widget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "autoapp_dep": {
                "models": [],
                "default_connection": "default",
                "migrations": module_path,
            }
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    assert len(changes) == 1
    writer = changes[0]
    assert writer.dependencies == [("autoapp_dep", "0001_initial")]
    assert writer.name == "0002_auto_20240101_1200"
    assert writer.initial is False


@pytest.mark.asyncio
async def test_autodetector_adds_relation_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app1_module = _write_migration(tmp_path, "autoapp1", "0001_initial")
    app2_module = _write_migration(tmp_path, "autoapp2", "0003_latest")
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    Team = _make_model("Team", "autoapp2", id=fields.IntField(pk=True))
    Widget = _make_model(
        "Widget",
        "autoapp1",
        id=fields.IntField(pk=True),
        team=fields.ForeignKeyField("autoapp2.Team"),
    )
    apps.register_model("autoapp2", Team)
    apps.register_model("autoapp1", Widget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "autoapp1": {"models": [], "default_connection": "default", "migrations": app1_module},
            "autoapp2": {"models": [], "default_connection": "default", "migrations": app2_module},
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    assert len(changes) == 2
    writer1 = next(writer for writer in changes if writer.app_label == "autoapp1")
    assert ("autoapp2", "0003_latest") in writer1.dependencies


@pytest.mark.asyncio
async def test_autodetector_multi_leaf_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = _write_migration(tmp_path, "branchapp", "0001_alpha")
    _write_migration(tmp_path, "branchapp", "0002_beta")
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    Widget = _make_model("Widget", "branchapp", id=fields.IntField(pk=True))
    apps.register_model("branchapp", Widget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "branchapp": {
                "models": [],
                "default_connection": "default",
                "migrations": module_path,
            }
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    assert len(changes) == 1
    writer = changes[0]
    assert set(writer.dependencies) == {
        ("branchapp", "0001_alpha"),
        ("branchapp", "0002_beta"),
    }


@pytest.mark.asyncio
async def test_autodetector_model_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = _write_migration_with_ops(
        tmp_path,
        "renameapp",
        "0001_initial",
        [
            "        ops.CreateModel(",
            "            name='OldWidget',",
            "            fields=[",
            "                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),",
            "                ('name', fields.CharField(max_length=100)),",
            "            ],",
            "        ),",
        ],
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    attrs = {
        "id": fields.IntField(pk=True),
        "name": fields.CharField(max_length=100),
    }
    meta = type("Meta", (), {"app": "renameapp", "table": "newwidget"})
    attrs["Meta"] = meta
    NewWidget = type("NewWidget", (Model,), attrs)
    apps.register_model("renameapp", NewWidget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "renameapp": {
                "models": [],
                "default_connection": "default",
                "migrations": module_path,
            }
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    assert len(changes) == 1
    ops = changes[0].operations
    assert any(isinstance(op, RenameModel) for op in ops)


@pytest.mark.asyncio
async def test_autodetector_field_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = _write_migration_with_ops(
        tmp_path,
        "renamefield",
        "0001_initial",
        [
            "        ops.CreateModel(",
            "            name='Widget',",
            "            fields=[",
            "                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),",
            "                ('title', fields.CharField(max_length=100)),",
            "            ],",
            "        ),",
        ],
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    attrs = {
        "id": fields.IntField(pk=True),
        "name": fields.CharField(max_length=100, source_field="title"),
    }
    meta = type("Meta", (), {"app": "renamefield", "table": "widget"})
    attrs["Meta"] = meta
    Widget = type("Widget", (Model,), attrs)
    apps.register_model("renamefield", Widget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "renamefield": {
                "models": [],
                "default_connection": "default",
                "migrations": module_path,
            }
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    assert len(changes) == 1
    ops = changes[0].operations
    assert any(isinstance(op, RenameField) for op in ops)


@pytest.mark.asyncio
async def test_autodetector_skips_unmigrated_relation_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = _write_migration(tmp_path, "relapp", "0001_initial")
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    Team = _make_model("Team", "nomigs", id=fields.IntField(pk=True))
    Widget = _make_model(
        "Widget",
        "relapp",
        id=fields.IntField(pk=True),
        team=fields.ForeignKeyField("nomigs.Team"),
    )
    apps.register_model("nomigs", Team)
    apps.register_model("relapp", Widget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "relapp": {"models": [], "default_connection": "default", "migrations": module_path},
            "nomigs": {"models": [], "default_connection": "default", "migrations": None},
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    assert len(changes) == 1
    writer = changes[0]
    assert ("nomigs", "0001_initial") not in writer.dependencies


@pytest.mark.asyncio
async def test_autodetector_relation_dependency_model_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app1_module = _write_migration(tmp_path, "classrel1", "0001_initial")
    app2_module = _write_migration(tmp_path, "classrel2", "0002_latest")
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    Team = _make_model("Team", "classrel2", id=fields.IntField(pk=True))
    Widget = _make_model(
        "Widget",
        "classrel1",
        id=fields.IntField(pk=True),
        team=fields.ForeignKeyField(Team),
    )
    apps.register_model("classrel2", Team)
    apps.register_model("classrel1", Widget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "classrel1": {
                "models": [],
                "default_connection": "default",
                "migrations": app1_module,
            },
            "classrel2": {
                "models": [],
                "default_connection": "default",
                "migrations": app2_module,
            },
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    writer = next(writer for writer in changes if writer.app_label == "classrel1")
    assert ("classrel2", "0002_latest") in writer.dependencies


@pytest.mark.asyncio
async def test_autodetector_no_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = _write_migration_with_ops(
        tmp_path,
        "nochange",
        "0001_initial",
        [
            "        ops.CreateModel(",
            "            name='Widget',",
            "            fields=[",
            "                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),",
            "            ],",
            "        ),",
        ],
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps = StateApps()
    Widget = _make_model("Widget", "nochange", id=fields.IntField(pk=True))
    apps.register_model("nochange", Widget)

    autodetector = MigrationAutodetector(
        apps,
        {
            "nochange": {
                "models": [],
                "default_connection": "default",
                "migrations": module_path,
            }
        },
        now=lambda: dt.datetime(2024, 1, 1, 12, 0),
    )
    changes = await autodetector.changes()
    assert changes == []
