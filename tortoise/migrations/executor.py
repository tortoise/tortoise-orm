from __future__ import annotations

from collections.abc import Iterable
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

    async def migrate(
        self,
        targets: Iterable[MigrationTarget] | None = None,
        *,
        fake: bool = False,
        dry_run: bool = False,
    ) -> None:
        await self.loader.build_graph()
        schema_editor = self._schema_editor()
        await self.recorder.ensure_schema(schema_editor)

        applied = set(await self.recorder.applied_migrations())
        plan = self._migration_plan(targets, applied, self.loader.graph)

        state_cache: State | None = None
        for step in plan:
            key = MigrationKey(
                app_label=step.migration.app_label, name=step.migration.name
            )
            if step.backward:
                state_before = await self._project_state(applied, upto=key)
                if not fake:
                    await step.migration.unapply(
                        state_before, dry_run=dry_run, schema_editor=schema_editor
                    )
                if not dry_run:
                    await self.recorder.record_unapplied(key.app_label, key.name)
                applied.discard(key)
                state_cache = None
            else:
                if state_cache is None:
                    state_cache = await self._project_state(applied)
                if not fake:
                    await step.migration.apply(
                        state_cache, dry_run=dry_run, schema_editor=schema_editor
                    )
                if not dry_run:
                    await self.recorder.record_applied(key.app_label, key.name)
                applied.add(key)

    async def plan(
        self, targets: Iterable[MigrationTarget] | None = None
    ) -> list[PlanStep]:
        await self.loader.build_graph()
        applied = set(await self.recorder.applied_migrations())
        return self._migration_plan(targets, applied, self.loader.graph)

    def _schema_editor(self) -> BaseSchemaEditor:
        module = self.connection.__class__.__module__
        dialect = self.connection.capabilities.dialect
        if "sqlite" in module:
            return SqliteSchemaEditor(self.connection)
        if "asyncpg" in module:
            return AsyncpgSchemaEditor(self.connection)
        if "psycopg" in module:
            return PsycopgSchemaEditor(self.connection)
        if "mysql" in module:
            return MySQLSchemaEditor(self.connection)
        if "mssql" in module or "odbc" in module:
            return MSSQLSchemaEditor(self.connection)
        if "oracle" in module:
            return OracleSchemaEditor(self.connection)
        if dialect == "postgres":
            return BasePostgresSchemaEditor(self.connection)
        return BaseSchemaEditor(self.connection)

    async def _project_state(
        self, applied: set[MigrationKey], *, upto: MigrationKey | None = None
    ) -> State:
        state = State(models={}, apps=StateApps())
        for key in self._full_plan():
            if key not in applied:
                continue
            if upto and key == upto:
                break
            migration = self.loader.graph.nodes[key]
            await migration.apply(state, dry_run=True, schema_editor=None)
        return state

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
        target_list = list(targets) if targets is not None else [
            MigrationTarget(app_label=key.app_label, name=key.name)
            for key in graph.leaf_nodes()
        ]
        for target in target_list:
            if target.name == "__latest__":
                for leaf in graph.leaf_nodes(target.app_label):
                    leaf_target = MigrationTarget(app_label=leaf.app_label, name=leaf.name)
                    plan.extend(self._forward_plan(leaf_target, applied, graph))
                continue
            if target.name == "__first__":
                for leaf in graph.leaf_nodes(target.app_label):
                    leaf_target = MigrationTarget(app_label=leaf.app_label, name=leaf.name)
                    plan.extend(
                        self._backward_plan(
                            leaf_target, applied, graph, include_target=True
                        )
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
        for key in graph.forwards_plan(
            MigrationKey(app_label=target.app_label, name=target.name)
        ):
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
            key = MigrationKey(
                app_label=step.migration.app_label, name=step.migration.name
            )
            if key in seen:
                if seen[key] != step.backward:
                    raise ValueError(f"Conflicting migration directions for {key}")
                continue
            seen[key] = step.backward
            deduped.append(step)
        return deduped
