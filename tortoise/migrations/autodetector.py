from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable

from tortoise.apps import Apps
from tortoise.fields.relational import (
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
)
from tortoise.migrations.graph import MigrationKey
from tortoise.migrations.loader import MigrationLoader
from tortoise.migrations.migration import Migration
from tortoise.migrations.recorder import MigrationRecorder
from tortoise.migrations.schema_generator.operation_generator import OperationGenerator
from tortoise.migrations.schema_generator.state import ModelState, State
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.migrations.writer import MigrationWriter, migrations_module_path

RELATION_FIELDS = (ForeignKeyFieldInstance, OneToOneFieldInstance, ManyToManyFieldInstance)
MIGRATION_NUMBER_RE = re.compile(r"^(\d{4})_")


class _NoopRecorder(MigrationRecorder):
    def __init__(self) -> None:
        super().__init__(connection=None)

    async def applied_migrations(self) -> list[MigrationKey]:
        return []

    async def ensure_schema(self, _schema_editor) -> None:
        return None


class MigrationAutodetector:
    def __init__(
        self,
        apps: Apps,
        apps_config: dict[str, dict],
        *,
        now: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self.apps = apps
        self.apps_config = apps_config
        self._now = now or dt.datetime.now
        self.loader = MigrationLoader(apps_config, _NoopRecorder(), load=False)

    async def changes(self) -> list[MigrationWriter]:
        await self.loader.build_graph()
        old_state = await self._project_state()
        new_state = self._current_state()
        writers: list[MigrationWriter] = []
        for app_label, config in self.apps_config.items():
            migrations_module = config.get("migrations")
            if not migrations_module:
                continue
            operations = OperationGenerator(old_state, new_state).generate(app_labels=[app_label])
            if not operations:
                continue
            dependencies = self._dependencies_for_app(app_label, new_state)
            name, initial = self._migration_name(app_label, old_state, new_state)
            writers.append(
                MigrationWriter(
                    name,
                    app_label,
                    operations,
                    dependencies=dependencies,
                    initial=initial,
                    migrations_module=migrations_module,
                )
            )
        return writers

    async def write(self) -> list[str]:
        writers = await self.changes()
        return [str(writer.write()) for writer in writers]

    def _current_state(self) -> State:
        state = State(models={}, apps=StateApps())
        for app_label, models in self.apps.items():
            for model in models.values():
                state.models[(app_label, model.__name__)] = ModelState.make_from_model(
                    app_label, model
                )
        return state

    async def _project_state(self) -> State:
        state = State(models={}, apps=StateApps())
        for key in self._full_plan():
            migration = self.loader.graph.nodes[key]
            if not isinstance(migration, Migration):
                raise ValueError(f"Missing migration for {key}")
            await migration.apply(state, dry_run=True, schema_editor=None)
        return state

    def _full_plan(self) -> list[MigrationKey]:
        plan: list[MigrationKey] = []
        seen: set[MigrationKey] = set()
        for leaf in self.loader.graph.leaf_nodes():
            for key in self.loader.graph.forwards_plan(leaf):
                if key in seen:
                    continue
                seen.add(key)
                plan.append(key)
        return plan

    def _dependencies_for_app(self, app_label: str, new_state: State) -> list[tuple[str, str]]:
        deps: set[MigrationKey] = set()
        deps.update(self._leaf_nodes(app_label))
        deps.update(self._relation_dependencies(app_label, new_state))
        return sorted([(dep.app_label, dep.name) for dep in deps])

    def _relation_dependencies(self, app_label: str, new_state: State) -> set[MigrationKey]:
        deps: set[MigrationKey] = set()
        for (model_app, _model_name), model_state in new_state.models.items():
            if model_app != app_label:
                continue
            for field in model_state.fields.values():
                if not isinstance(field, RELATION_FIELDS):
                    continue
                model_name = field.model_name
                if isinstance(model_name, str):
                    related_app, _ = model_name.split(".", 1)
                else:
                    related_app_label = model_name._meta.app
                    if related_app_label is None:
                        continue
                    related_app = related_app_label
                if related_app == app_label:
                    continue
                if not self.apps_config.get(related_app, {}).get("migrations"):
                    continue
                deps.update(self._leaf_nodes(related_app))
        return deps

    def _leaf_nodes(self, app_label: str) -> list[MigrationKey]:
        try:
            nodes = list(self.loader.graph.leaf_nodes(app_label))
        except Exception:
            nodes = []
        if nodes:
            return nodes
        disk_nodes = sorted(
            [key for key in self.loader.disk_migrations if key.app_label == app_label]
        )
        if disk_nodes:
            return disk_nodes
        names = self._disk_migration_names(app_label)
        if names:
            return [MigrationKey(app_label=app_label, name=name) for name in names]
        return []

    def _disk_migration_names(self, app_label: str) -> list[str]:
        module_name = self.apps_config.get(app_label, {}).get("migrations")
        if not module_name:
            return []
        try:
            path = migrations_module_path(module_name)
        except Exception:
            return []
        names: list[str] = []
        for entry in path.iterdir():
            if not entry.is_file() or entry.suffix != ".py":
                continue
            name = entry.stem
            if name == "__init__" or name[0] in "_~":
                continue
            names.append(name)
        return sorted(names)

    def _migration_name(
        self, app_label: str, old_state: State, new_state: State
    ) -> tuple[str, bool]:
        new_has_models = any(key[0] == app_label for key in new_state.models)
        has_migrations = any(key.app_label == app_label for key in self.loader.graph.nodes)
        if not has_migrations and new_has_models:
            return "0001_initial", True
        next_number = self._next_number(app_label)
        timestamp = self._now().strftime("%Y%m%d_%H%M")
        return f"{next_number:04d}_auto_{timestamp}", False

    def _next_number(self, app_label: str) -> int:
        numbers = []
        for key in self.loader.graph.nodes:
            if key.app_label != app_label:
                continue
            match = MIGRATION_NUMBER_RE.match(key.name)
            if match:
                numbers.append(int(match.group(1)))
        if not numbers:
            for name in self._disk_migration_names(app_label):
                match = MIGRATION_NUMBER_RE.match(name)
                if match:
                    numbers.append(int(match.group(1)))
        if not numbers:
            return 1
        return max(numbers) + 1
