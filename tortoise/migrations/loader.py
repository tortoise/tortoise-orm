from __future__ import annotations

import pkgutil
import sys
from collections import deque
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
        all_apps_config: dict[str, dict] | None = None,
    ) -> None:
        # all_apps_config is the full app config; apps_config is the subset being
        # executed. Dependencies may point into all_apps_config, so keep both.
        # all_apps_config must be a superset of apps_config — migrations_module()
        # falls back to it when an app isn't in apps_config.
        self.apps_config = dict(apps_config)
        self.all_apps_config = dict(all_apps_config if all_apps_config is not None else apps_config)
        self.recorder = recorder
        self.disk_migrations: dict[MigrationKey, Migration] = {}
        self.applied_migrations: set[MigrationKey] = set()
        self.unmigrated_apps: set[str] = set()
        self.migrated_apps: set[str] = set()
        self.graph = MigrationGraph()
        if load:
            raise RuntimeError("MigrationLoader.build_graph is async; call it explicitly.")

    def migrations_module(self, app_label: str) -> str | None:
        try:
            app_config = self.apps_config[app_label]
        except KeyError:
            app_config = self.all_apps_config.get(app_label, {})
        return app_config.get("migrations")

    def _load_app_disk(self, app_label: str) -> list[Migration]:
        module_name = self.migrations_module(app_label)
        if not module_name:
            self.unmigrated_apps.add(app_label)
            return []

        was_loaded = module_name in sys.modules
        try:
            # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
            module = import_module(module_name)
        except ModuleNotFoundError:
            raise
        else:
            if not hasattr(module, "__path__"):
                self.unmigrated_apps.add(app_label)
                return []
            if was_loaded:
                reload(module)

        self.migrated_apps.add(app_label)
        migration_names = [
            name
            for _, name, is_pkg in pkgutil.iter_modules(module.__path__)
            if not is_pkg and name[0] not in "_~"
        ]
        app_migrations: list[Migration] = []
        for migration_name in migration_names:
            migration_path = f"{module_name}.{migration_name}"
            # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
            migration_module = import_module(migration_path)
            if not hasattr(migration_module, "Migration"):
                raise ValueError(
                    f"Migration {migration_name} in app {app_label} has no Migration class"
                )
            migration_cls = migration_module.Migration
            migration_obj = migration_cls(migration_name, app_label)
            key = MigrationKey(app_label=app_label, name=migration_name)
            self.disk_migrations[key] = migration_obj
            app_migrations.append(migration_obj)
        return app_migrations

    def load_disk(self) -> None:
        # Selected apps are the entry points, but their dependencies may live in apps
        # that weren't selected. Walk dependencies/run_before iteratively and pull in
        # any app present in all_apps_config, so StateApps can resolve cross-app FKs.
        self.disk_migrations = {}
        self.unmigrated_apps = set()
        self.migrated_apps = set()
        loaded_apps: set[str] = set()
        apps_to_load = deque(self.apps_config.keys())
        while apps_to_load:
            app_label = apps_to_load.popleft()
            if app_label in loaded_apps:
                continue
            loaded_apps.add(app_label)
            if app_migrations := self._load_app_disk(app_label):
                self._enqueue_dependencies(app_migrations, loaded_apps, apps_to_load)

    def _enqueue_dependencies(
        self, app_migrations: list[Migration], loaded_apps: set[str], apps_to_load: deque[str]
    ) -> None:
        unloaded_apps = self.all_apps_config.keys() - loaded_apps
        for migration in app_migrations:
            for parent in migration.dependencies:
                if parent[0] in unloaded_apps:
                    apps_to_load.append(parent[0])
            for child in migration.run_before:
                if child[0] in unloaded_apps:
                    apps_to_load.append(child[0])

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
