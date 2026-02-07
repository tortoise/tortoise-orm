from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.migrations.graph import MigrationGraph, MigrationKey
from tortoise.migrations.loader import MigrationLoader
from tortoise.migrations.migration import Migration
from tortoise.migrations.recorder import MigrationRecorder
from tortoise.migrations.schema_editor import (
    AsyncpgSchemaEditor,
    BasePostgresSchemaEditor,
    BaseSchemaEditor,
    MSSQLSchemaEditor,
    MySQLSchemaEditor,
    OracleSchemaEditor,
    PsycopgSchemaEditor,
    SqliteSchemaEditor,
)
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.transactions import in_transaction


@dataclass(frozen=True)
class PlanStep:
    migration: Migration
    backward: bool


@dataclass(frozen=True)
class MigrationTarget:
    app_label: str
    name: str


class MigrationExecutor:
    def __init__(self, connection: BaseDBAsyncClient, apps_config: dict[str, dict]) -> None:
        self.connection = connection
        self.recorder = MigrationRecorder(connection)
        self.loader = MigrationLoader(apps_config, self.recorder, load=False)
        self._full_plan_cache: list[MigrationKey] | None = None
        self._logger = logging.getLogger(__name__)

    async def migrate(
        self,
        targets: Iterable[MigrationTarget] | None = None,
        *,
        fake: bool = False,
        dry_run: bool = False,
        direction: str = "both",
        progress: Callable[[str, str, str], object] | None = None,
    ) -> None:
        self._logger.debug("Building migration graph")
        await self.loader.build_graph()

        # Create a non-atomic schema editor for recorder operations only
        recorder_schema_editor = self._schema_editor(atomic=False)
        self._logger.debug("Ensuring migration schema")
        await self.recorder.ensure_schema(recorder_schema_editor)

        self._logger.debug("Loading applied migrations")
        applied = set(await self.recorder.applied_migrations())

        self._logger.debug("Building migration plan")
        plan = self._migration_plan(targets, applied, self.loader.graph)
        self._validate_plan_direction(plan, direction)

        state_cache_by_key: dict[MigrationKey, State] | None = None
        if any(step.backward for step in plan):
            self._logger.debug("Building rollback state cache")
            state_cache_by_key = await self._project_state_cache(applied)

        state_cache: State | None = None
        for step in plan:
            key = MigrationKey(app_label=step.migration.app_label, name=step.migration.name)
            if step.backward:
                if state_cache_by_key is not None:
                    state_before = state_cache_by_key[key]
                else:
                    state_before = await self._project_state(applied, upto=key)
                if not fake:
                    self._emit(progress, "rollback_start", key)
                    schema_editor = self._schema_editor(atomic=step.migration.atomic)
                    if schema_editor.atomic_migration:
                        async with in_transaction(self.connection.connection_name) as txn_client:
                            schema_editor.client = txn_client
                            await step.migration.unapply(
                                state_before, dry_run=dry_run, schema_editor=schema_editor
                            )
                    else:
                        await step.migration.unapply(
                            state_before, dry_run=dry_run, schema_editor=schema_editor
                        )
                    self._emit(progress, "rollback_done", key)
                if not dry_run:
                    await self.recorder.record_unapplied(key.app_label, key.name)
                applied.discard(key)
                state_cache = None
            else:
                if state_cache is None:
                    state_cache = await self._project_state(applied)
                if not fake:
                    self._emit(progress, "apply_start", key)
                    schema_editor = self._schema_editor(atomic=step.migration.atomic)
                    if schema_editor.atomic_migration:
                        async with in_transaction(self.connection.connection_name) as txn_client:
                            schema_editor.client = txn_client
                            await step.migration.apply(
                                state_cache, dry_run=dry_run, schema_editor=schema_editor
                            )
                    else:
                        await step.migration.apply(
                            state_cache, dry_run=dry_run, schema_editor=schema_editor
                        )
                    self._emit(progress, "apply_done", key)
                if not dry_run:
                    await self.recorder.record_applied(key.app_label, key.name)
                applied.add(key)

    async def plan(self, targets: Iterable[MigrationTarget] | None = None) -> list[PlanStep]:
        await self.loader.build_graph()
        applied = set(await self.recorder.applied_migrations())
        return self._migration_plan(targets, applied, self.loader.graph)

    @staticmethod
    def _emit(
        progress: Callable[[str, str, str], object] | None,
        event: str,
        key: MigrationKey,
    ) -> None:
        if progress is not None:
            progress(event, key.app_label, key.name)

    def _schema_editor(self, atomic: bool = True, collect_sql: bool = False) -> BaseSchemaEditor:
        module = self.connection.__class__.__module__
        dialect = self.connection.capabilities.dialect
        if "sqlite" in module:
            return SqliteSchemaEditor(self.connection, atomic=atomic, collect_sql=collect_sql)
        if "asyncpg" in module:
            return AsyncpgSchemaEditor(self.connection, atomic=atomic, collect_sql=collect_sql)
        if "psycopg" in module:
            return PsycopgSchemaEditor(self.connection, atomic=atomic, collect_sql=collect_sql)
        if "mysql" in module:
            return MySQLSchemaEditor(self.connection, atomic=atomic, collect_sql=collect_sql)
        if "mssql" in module or "odbc" in module:
            return MSSQLSchemaEditor(self.connection, atomic=atomic, collect_sql=collect_sql)
        if "oracle" in module:
            return OracleSchemaEditor(self.connection, atomic=atomic, collect_sql=collect_sql)
        if dialect == "postgres":
            return BasePostgresSchemaEditor(self.connection, atomic=atomic, collect_sql=collect_sql)
        return BaseSchemaEditor(self.connection, atomic=atomic, collect_sql=collect_sql)

    async def collect_sql(
        self,
        app_label: str,
        migration_name: str,
        *,
        backward: bool = False,
    ) -> list[str]:
        """Collect SQL statements for a single migration without executing them.

        Args:
            app_label: The application label.
            migration_name: The migration name (exact or prefix match).
            backward: If True, collect SQL for unapplying the migration.

        Returns:
            A list of SQL strings (including comment annotations).
        """
        await self.loader.build_graph()

        # Resolve migration key — support prefix matching
        key = self._resolve_migration_key(app_label, migration_name)
        migration = self.loader.graph.nodes[key]
        if not isinstance(migration, Migration):
            raise ValueError(f"Missing migration for {key}")

        # For SQL collection we don't need the real database — treat all
        # migrations in the graph as "applied" so _project_state replays
        # them up to the target.
        all_keys = set(self.loader.graph.nodes.keys())
        state = await self._project_state(all_keys, upto=key)

        editor = self._schema_editor(atomic=False, collect_sql=True)

        if backward:
            await migration.unapply(state, schema_editor=editor, collect_sql=True)
        else:
            await migration.apply(state, schema_editor=editor, collect_sql=True)

        return editor.collected_sql

    def _resolve_migration_key(self, app_label: str, migration_name: str) -> MigrationKey:
        """Resolve a migration name to a MigrationKey, supporting prefix matching."""
        exact_key = MigrationKey(app_label=app_label, name=migration_name)
        if exact_key in self.loader.graph.nodes:
            return exact_key

        # Try prefix matching
        matches = [
            key
            for key in self.loader.graph.nodes
            if key.app_label == app_label and key.name.startswith(migration_name)
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(m.name for m in matches)
            raise ValueError(
                f"Ambiguous migration name {migration_name!r} for app {app_label!r}. "
                f"Matches: {names}"
            )
        raise ValueError(f"Cannot find migration {migration_name!r} in app {app_label!r}")

    async def _project_state(
        self, applied: set[MigrationKey], *, upto: MigrationKey | None = None
    ) -> State:
        default_connections = {
            label: config.get("default_connection", "default")
            for label, config in self.loader.apps_config.items()
        }
        state = State(models={}, apps=StateApps(default_connections=default_connections))
        for key in self._full_plan():
            if key not in applied:
                continue
            if upto and key == upto:
                break
            migration = self.loader.graph.nodes[key]
            if migration is None:
                raise ValueError(f"Missing migration for {key}")
            await migration.apply(state, dry_run=True, schema_editor=None)
        return state

    async def _project_state_cache(self, applied: set[MigrationKey]) -> dict[MigrationKey, State]:
        default_connections = {
            label: config.get("default_connection", "default")
            for label, config in self.loader.apps_config.items()
        }
        state = State(models={}, apps=StateApps(default_connections=default_connections))
        cache: dict[MigrationKey, State] = {}
        for key in self._full_plan():
            if key not in applied:
                continue
            cache[key] = state.clone()
            migration = self.loader.graph.nodes[key]
            if migration is None:
                raise ValueError(f"Missing migration for {key}")
            await migration.apply(state, dry_run=True, schema_editor=None)
        return cache

    def _full_plan(self) -> list[MigrationKey]:
        if self._full_plan_cache is not None:
            return list(self._full_plan_cache)
        plan: list[MigrationKey] = []
        seen: set[MigrationKey] = set()
        for leaf in self.loader.graph.leaf_nodes():
            for key in self.loader.graph.forwards_plan(leaf):
                if key in seen:
                    continue
                seen.add(key)
                plan.append(key)
        self._full_plan_cache = list(plan)
        return plan

    def _migration_plan(
        self,
        targets: Iterable[MigrationTarget] | None,
        applied: set[MigrationKey],
        graph: MigrationGraph,
    ) -> list[PlanStep]:
        plan: list[PlanStep] = []
        target_list = (
            list(targets)
            if targets is not None
            else [
                MigrationTarget(app_label=key.app_label, name=key.name)
                for key in graph.leaf_nodes()
            ]
        )
        for target in target_list:
            if target.name == "__latest__":
                for leaf in graph.leaf_nodes(target.app_label):
                    leaf_target = MigrationTarget(app_label=leaf.app_label, name=leaf.name)
                    plan.extend(self._forward_plan(leaf_target, applied, graph))
                continue
            if target.name == "__first__":
                for root in graph.root_nodes(target.app_label):
                    root_target = MigrationTarget(app_label=root.app_label, name=root.name)
                    plan.extend(
                        self._backward_plan(root_target, applied, graph, include_target=True)
                    )
                continue
            key = MigrationKey(app_label=target.app_label, name=target.name)
            if key not in graph.nodes:
                raise ValueError(f"Unknown migration target {key}")
            if key in applied:
                plan.extend(self._backward_plan(target, applied, graph))
            else:
                plan.extend(self._forward_plan(target, applied, graph))
        return self._dedupe_plan(plan)

    def _forward_plan(
        self,
        target: MigrationTarget,
        applied: set[MigrationKey],
        graph: MigrationGraph,
    ) -> list[PlanStep]:
        plan: list[PlanStep] = []
        for key in graph.forwards_plan(MigrationKey(app_label=target.app_label, name=target.name)):
            if key in applied:
                continue
            migration = graph.nodes[key]
            if not isinstance(migration, Migration):
                raise ValueError(f"Missing migration for {key}")
            plan.append(PlanStep(migration=migration, backward=False))
        return plan

    def _backward_plan(
        self,
        target: MigrationTarget,
        applied: set[MigrationKey],
        graph: MigrationGraph,
        *,
        include_target: bool = False,
    ) -> list[PlanStep]:
        plan: list[PlanStep] = []
        target_key = MigrationKey(app_label=target.app_label, name=target.name)
        for key in graph.backwards_plan(target_key):
            if key not in applied:
                continue
            if not include_target and key == target_key:
                continue
            migration = graph.nodes[key]
            if not isinstance(migration, Migration):
                raise ValueError(f"Missing migration for {key}")
            plan.append(PlanStep(migration=migration, backward=True))
        return plan

    def _dedupe_plan(self, plan: list[PlanStep]) -> list[PlanStep]:
        deduped: list[PlanStep] = []
        seen: dict[MigrationKey, bool] = {}
        for step in plan:
            key = MigrationKey(app_label=step.migration.app_label, name=step.migration.name)
            if key in seen:
                if seen[key] != step.backward:
                    raise ValueError(f"Conflicting migration directions for {key}")
                continue
            seen[key] = step.backward
            deduped.append(step)
        return deduped

    @staticmethod
    def _validate_plan_direction(plan: list[PlanStep], direction: str) -> None:
        if direction == "both":
            return
        if direction not in {"forward", "backward"}:
            raise ValueError(f"Unknown migration direction {direction!r}")
        if direction == "forward" and any(step.backward for step in plan):
            raise ValueError("Backward migrations are not allowed in this mode")
        if direction == "backward" and any(not step.backward for step in plan):
            raise ValueError("Forward migrations are not allowed in this mode")
