from __future__ import annotations

import importlib
from pathlib import Path
from typing import cast

import pytest

from tortoise.backends.base.client import BaseDBAsyncClient, Capabilities
from tortoise.context import TortoiseContext
from tortoise.migrations.executor import MigrationExecutor, MigrationTarget
from tortoise.migrations.graph import MigrationGraph, MigrationKey
from tortoise.migrations.loader import MigrationLoader
from tortoise.migrations.migration import Migration
from tortoise.migrations.operations import TortoiseOperation
from tortoise.migrations.recorder import MigrationRecorder
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps


class FakeConnection:
    def __init__(self, *, applied: list[MigrationKey] | None = None) -> None:
        self.capabilities = Capabilities("sqlite", inline_comment=True)
        self.connection_name = "default"
        self._applied = applied or []
        self.executed_scripts: list[str] = []

    async def execute_query(self, query: str, values: list | None = None):
        _ = (query, values)
        rows = [{"app": key.app_label, "name": key.name} for key in self._applied]
        return 0, rows

    async def execute_script(self, query: str) -> None:
        self.executed_scripts.append(query)


def _write_migrations(
    tmp_path: Path, app_label: str, migrations: list[tuple[str, list[tuple[str, str]]]]
) -> str:
    package_dir = tmp_path / app_label
    migrations_dir = package_dir / "migrations"
    migrations_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="ascii")
    (migrations_dir / "__init__.py").write_text("", encoding="ascii")
    for name, dependencies in migrations:
        content = [
            "from tortoise import migrations",
            "",
            "class Migration(migrations.Migration):",
            f"    dependencies = {dependencies!r}",
            "",
            "    operations = []",
            "",
        ]
        (migrations_dir / f"{name}.py").write_text("\n".join(content), encoding="ascii")
    return f"{app_label}.migrations"


def _write_runpython_migrations(tmp_path: Path, app_label: str) -> str:
    package_dir = tmp_path / app_label
    migrations_dir = package_dir / "migrations"
    migrations_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="ascii")
    (migrations_dir / "__init__.py").write_text("", encoding="ascii")

    (migrations_dir / "0001_initial.py").write_text(
        "\n".join(
            [
                "from tortoise import migrations",
                "from tortoise import fields",
                "from tortoise.migrations import operations as ops",
                "",
                "class Migration(migrations.Migration):",
                "    dependencies = []",
                "",
                "    operations = [",
                "        ops.CreateModel(",
                "            name='Post',",
                "            fields=[",
                "                ('id', fields.IntField(pk=True)),",
                "                ('title', fields.CharField(max_length=200)),",
                "                ('summary', fields.TextField(null=True)),",
                "            ],",
                "        ),",
                "    ]",
                "",
            ]
        ),
        encoding="ascii",
    )

    (migrations_dir / "0002_runpython.py").write_text(
        "\n".join(
            [
                "from tortoise import migrations",
                "from tortoise.expressions import F",
                "from tortoise.migrations import operations as ops",
                "",
                "CALLS = []",
                "",
                "",
                "async def populate_summary(apps, schema_editor) -> None:",
                "    CALLS.append('forward')",
                "    Post = apps.get_model('blog.Post')",
                "    await Post.filter(summary=None).update(summary=F('title'))",
                "",
                "",
                "async def reset_summary(apps, schema_editor) -> None:",
                "    CALLS.append('reverse')",
                "    Post = apps.get_model('blog.Post')",
                "    await Post.all().update(summary=None)",
                "",
                "",
                "class Migration(migrations.Migration):",
                "    dependencies = [('blog', '0001_initial')]",
                "",
                "    operations = [",
                "        ops.RunPython(",
                "            code=populate_summary,",
                "            reverse_code=reset_summary,",
                "        ),",
                "    ]",
                "",
            ]
        ),
        encoding="ascii",
    )

    (migrations_dir / "0003_rename_excerpt.py").write_text(
        "\n".join(
            [
                "from tortoise import migrations",
                "from tortoise.migrations import operations as ops",
                "",
                "class Migration(migrations.Migration):",
                "    dependencies = [('blog', '0002_runpython')]",
                "",
                "    operations = [",
                "        ops.RenameField(",
                "            model_name='Post',",
                "            old_name='summary',",
                "            new_name='excerpt',",
                "        ),",
                "    ]",
                "",
            ]
        ),
        encoding="ascii",
    )

    return f"{app_label}.migrations"


@pytest.mark.asyncio
async def test_graph_planning_with_keys() -> None:
    graph = MigrationGraph()
    key1 = MigrationKey(app_label="models", name="0001_initial")
    key2 = MigrationKey(app_label="models", name="0002_second")
    graph.add_node(key1, Migration(key1.name, key1.app_label))
    graph.add_node(key2, Migration(key2.name, key2.app_label))
    graph.add_dependency(key2, key2, key1)

    assert graph.forwards_plan(key2) == [key1, key2]
    assert graph.backwards_plan(key1) == [key2, key1]


@pytest.mark.asyncio
async def test_graph_multi_app_dependencies() -> None:
    graph = MigrationGraph()
    a1 = MigrationKey(app_label="app1", name="0001_initial")
    a2 = MigrationKey(app_label="app1", name="0002_second")
    b1 = MigrationKey(app_label="app2", name="0001_initial")
    graph.add_node(a1, Migration(a1.name, a1.app_label))
    graph.add_node(a2, Migration(a2.name, a2.app_label))
    graph.add_node(b1, Migration(b1.name, b1.app_label))
    graph.add_dependency(a2, a2, a1)
    graph.add_dependency(b1, b1, a2)

    assert graph.forwards_plan(b1) == [a1, a2, b1]


@pytest.mark.asyncio
async def test_loader_builds_graph(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = _write_migrations(
        tmp_path,
        "app",
        [
            ("0001_initial", []),
            ("0002_second", [("app", "0001_initial")]),
        ],
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps_config = {
        "app": {"models": [], "default_connection": "default", "migrations": module_path}
    }

    class FakeRecorder:
        async def applied_migrations(self):
            return []

    loader = MigrationLoader(apps_config, cast(MigrationRecorder, FakeRecorder()), load=False)
    await loader.build_graph()

    key1 = MigrationKey(app_label="app", name="0001_initial")
    key2 = MigrationKey(app_label="app", name="0002_second")
    assert key1 in loader.graph.nodes
    assert key2 in loader.graph.nodes
    assert loader.graph.forwards_plan(key2) == [key1, key2]


@pytest.mark.asyncio
async def test_loader_missing_module_raises(tmp_path: Path) -> None:
    apps_config = {
        "app": {"models": [], "default_connection": "default", "migrations": "nope.migrations"}
    }

    class FakeRecorder:
        async def applied_migrations(self):
            return []

    loader = MigrationLoader(apps_config, cast(MigrationRecorder, FakeRecorder()), load=False)
    with pytest.raises(ModuleNotFoundError):
        await loader.build_graph()


@pytest.mark.asyncio
async def test_executor_plan_forward_and_backward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = _write_migrations(
        tmp_path,
        "app",
        [
            ("0001_initial", []),
            ("0002_second", [("app", "0001_initial")]),
        ],
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps_config = {
        "app": {"models": [], "default_connection": "default", "migrations": module_path}
    }
    connection = FakeConnection()
    executor = MigrationExecutor(cast(BaseDBAsyncClient, connection), apps_config)

    steps = await executor.plan()
    assert [step.backward for step in steps] == [False, False]
    assert [step.migration.name for step in steps] == ["0001_initial", "0002_second"]

    applied = [
        MigrationKey(app_label="app", name="0001_initial"),
        MigrationKey(app_label="app", name="0002_second"),
    ]
    connection = FakeConnection(applied=applied)
    executor = MigrationExecutor(cast(BaseDBAsyncClient, connection), apps_config)
    steps = await executor.plan([MigrationTarget(app_label="app", name="__first__")])
    assert [step.backward for step in steps] == [True, True]
    assert [step.migration.name for step in steps] == ["0002_second", "0001_initial"]


@pytest.mark.asyncio
async def test_executor_blocks_backward_when_forward_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = _write_migrations(
        tmp_path,
        "app",
        [
            ("0001_initial", []),
            ("0002_second", [("app", "0001_initial")]),
        ],
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps_config = {
        "app": {"models": [], "default_connection": "default", "migrations": module_path}
    }
    applied = [
        MigrationKey(app_label="app", name="0001_initial"),
        MigrationKey(app_label="app", name="0002_second"),
    ]
    connection = FakeConnection(applied=applied)
    executor = MigrationExecutor(cast(BaseDBAsyncClient, connection), apps_config)

    with pytest.raises(ValueError, match="Backward migrations are not allowed"):
        await executor.migrate(
            [MigrationTarget(app_label="app", name="0001_initial")],
            direction="forward",
        )


@pytest.mark.asyncio
async def test_executor_blocks_forward_when_backward_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = _write_migrations(
        tmp_path,
        "app",
        [
            ("0001_initial", []),
            ("0002_second", [("app", "0001_initial")]),
        ],
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps_config = {
        "app": {"models": [], "default_connection": "default", "migrations": module_path}
    }
    connection = FakeConnection()
    executor = MigrationExecutor(cast(BaseDBAsyncClient, connection), apps_config)

    with pytest.raises(ValueError, match="Forward migrations are not allowed"):
        await executor.migrate(
            [MigrationTarget(app_label="app", name="0001_initial")],
            direction="backward",
        )


@pytest.mark.asyncio
async def test_executor_plan_cross_app_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app1_module = _write_migrations(tmp_path, "app1", [("0001_initial", [])])
    app2_module = _write_migrations(
        tmp_path, "app2", [("0001_initial", [("app1", "0001_initial")])]
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps_config = {
        "app1": {"models": [], "default_connection": "default", "migrations": app1_module},
        "app2": {"models": [], "default_connection": "default", "migrations": app2_module},
    }
    connection = FakeConnection()
    executor = MigrationExecutor(cast(BaseDBAsyncClient, connection), apps_config)

    steps = await executor.plan([MigrationTarget(app_label="app2", name="__latest__")])
    assert [step.migration.app_label for step in steps] == ["app1", "app2"]
    assert [step.migration.name for step in steps] == ["0001_initial", "0001_initial"]


@pytest.mark.asyncio
async def test_migration_apply_and_unapply_flags() -> None:
    class MarkerOperation(TortoiseOperation):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def state_forward(self, app_label: str, state: State) -> None:
            self.calls.append("state_forward")

        async def database_forward(self, app_label, old_state, new_state, state_editor):
            self.calls.append("database_forward")

        async def database_backward(self, app_label, old_state, new_state, state_editor):
            self.calls.append("database_backward")

    class TestMigration(Migration):
        operations = [MarkerOperation()]

    migration = TestMigration("0001_initial", "models")
    state = State(models={}, apps=StateApps())

    await migration.apply(state, dry_run=True, schema_editor=None)
    marker = cast(MarkerOperation, migration.operations[0])
    assert marker.calls == ["state_forward"]

    await migration.unapply(state, dry_run=True, schema_editor=None)
    marker = cast(MarkerOperation, migration.operations[0])
    assert marker.calls == ["state_forward", "state_forward"]


@pytest.mark.asyncio
async def test_migration_unapply_requires_reversible() -> None:
    class IrreversibleOperation(TortoiseOperation):
        reversible = False

    class TestMigration(Migration):
        operations = [IrreversibleOperation()]

    migration = TestMigration("0001_initial", "models")
    state = State(models={}, apps=StateApps())

    with pytest.raises(ValueError):
        await migration.unapply(state, dry_run=True, schema_editor=None)


@pytest.mark.asyncio
async def test_recorder_reads_and_writes() -> None:
    applied = [MigrationKey(app_label="app", name="0001_initial")]
    connection = FakeConnection(applied=applied)
    recorder = MigrationRecorder(connection)

    rows = await recorder.applied_migrations()
    assert rows == applied

    await recorder.record_applied("app", "0002_second")
    await recorder.record_unapplied("app", "0001_initial")
    assert any("INSERT INTO" in query for query in connection.executed_scripts)
    assert any("DELETE FROM" in query for query in connection.executed_scripts)


@pytest.mark.asyncio
async def test_executor_plan_ordering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module_path = _write_migrations(
        tmp_path,
        "app",
        [
            ("0001_initial", []),
            ("0002_second", [("app", "0001_initial")]),
        ],
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    apps_config = {
        "app": {"models": [], "default_connection": "default", "migrations": module_path}
    }
    connection = FakeConnection()
    executor = MigrationExecutor(cast(BaseDBAsyncClient, connection), apps_config)
    steps = await executor.plan([MigrationTarget(app_label="app", name="__latest__")])

    assert [step.migration.name for step in steps] == ["0001_initial", "0002_second"]


@pytest.mark.asyncio
async def test_runpython_historical_models_survive_schema_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = _write_runpython_migrations(tmp_path, "blog")
    monkeypatch.syspath_prepend(str(tmp_path))

    async with TortoiseContext() as ctx:
        ctx.connections._init_config(
            {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": str(tmp_path / "runpython.sqlite3")},
                }
            }
        )
        apps_config = {
            "blog": {
                "models": [],
                "default_connection": "default",
                "migrations": module_path,
            }
        }
        connection = ctx.connections.get("default")
        executor = MigrationExecutor(connection, apps_config)

        await executor.migrate()
        module = importlib.import_module(f"{module_path}.0002_runpython")
        assert module.CALLS == ["forward"]

        await executor.migrate([MigrationTarget(app_label="blog", name="0001_initial")])
        assert module.CALLS == ["forward", "reverse"]

        await executor.migrate([MigrationTarget(app_label="blog", name="__latest__")])
        assert module.CALLS == ["forward", "reverse", "forward"]

        await connection.close()
