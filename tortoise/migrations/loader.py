from __future__ import annotations

import pkgutil
import sys
from importlib import import_module, reload

from tortoise.migrations.graph import MigrationGraph, MigrationKey
from tortoise.migrations.migration import Migration
from tortoise.migrations.recorder import MigrationRecorder


class MigrationLoader:
    def __init__(
        self,
        apps_config: dict[str, dict],
        recorder: MigrationRecorder,
        *,
        load: bool = False,
    ) -> None:
        self.apps_config = apps_config
        self.recorder = recorder
        self.disk_migrations: dict[MigrationKey, Migration] = {}
        self.applied_migrations: set[MigrationKey] = set()
        self.unmigrated_apps: set[str] = set()
        self.migrated_apps: set[str] = set()
        self.graph = MigrationGraph()
        if load:
            raise RuntimeError("MigrationLoader.build_graph is async; call it explicitly.")

    def migrations_module(self, app_label: str) -> str | None:
        return self.apps_config.get(app_label, {}).get("migrations")

    def load_disk(self) -> None:
        self.disk_migrations = {}
        self.unmigrated_apps = set()
        self.migrated_apps = set()
        for app_label in self.apps_config:
            module_name = self.migrations_module(app_label)
            if not module_name:
                self.unmigrated_apps.add(app_label)
                continue

            was_loaded = module_name in sys.modules
            try:
                module = import_module(module_name)
            except ModuleNotFoundError:
                raise
            else:
                if not hasattr(module, "__path__"):
                    self.unmigrated_apps.add(app_label)
                    continue
                if was_loaded:
                    reload(module)

            self.migrated_apps.add(app_label)
            migration_names = [
                name
                for _, name, is_pkg in pkgutil.iter_modules(module.__path__)
                if not is_pkg and name[0] not in "_~"
            ]
            for migration_name in migration_names:
                migration_path = f"{module_name}.{migration_name}"
                migration_module = import_module(migration_path)
                if not hasattr(migration_module, "Migration"):
                    raise ValueError(
                        f"Migration {migration_name} in app {app_label} has no Migration class"
                    )
                migration_cls = migration_module.Migration
                migration_obj = migration_cls(migration_name, app_label)
                key = MigrationKey(app_label=app_label, name=migration_name)
                self.disk_migrations[key] = migration_obj

    async def build_graph(self) -> None:
        self.load_disk()
        self.graph = MigrationGraph()
        self.applied_migrations = set(await self.recorder.applied_migrations())

        for key, migration in self.disk_migrations.items():
            self.graph.add_node(key, migration)

        for key, migration in self.disk_migrations.items():
            self._add_internal_dependencies(key, migration)

        for key, migration in self.disk_migrations.items():
            self._add_external_dependencies(key, migration)

        self.graph.validate_consistency()

    def _check_key(self, key: MigrationKey, current_app: str) -> MigrationKey | None:
        if (key.name != "__first__" and key.name != "__latest__") or key in self.graph.nodes:
            return key
        if key.app_label == current_app:
            return None
        if key.app_label in self.unmigrated_apps:
            return None
        if key.app_label in self.migrated_apps:
            try:
                if key.name == "__first__":
                    return self.graph.root_nodes(key.app_label)[0]
                return self.graph.leaf_nodes(key.app_label)[0]
            except IndexError as exc:
                raise ValueError(f"Dependency on app with no migrations: {key.app_label}") from exc
        raise ValueError(f"Dependency on unknown app: {key.app_label}")

    def _add_internal_dependencies(self, key: MigrationKey, migration: Migration) -> None:
        for parent in migration.dependencies:
            parent_key = MigrationKey(app_label=parent[0], name=parent[1])
            if parent_key.app_label == key.app_label and parent_key.name != "__first__":
                self.graph.add_dependency(key, key, parent_key, skip_validation=True)

    def _add_external_dependencies(self, key: MigrationKey, migration: Migration) -> None:
        for parent in migration.dependencies:
            parent_key = MigrationKey(app_label=parent[0], name=parent[1])
            if key.app_label == parent_key.app_label:
                continue
            checked = self._check_key(parent_key, key.app_label)
            if checked is not None:
                self.graph.add_dependency(key, key, checked, skip_validation=True)
        for child in migration.run_before:
            child_key = MigrationKey(app_label=child[0], name=child[1])
            checked = self._check_key(child_key, key.app_label)
            if checked is not None:
                self.graph.add_dependency(key, checked, key, skip_validation=True)
