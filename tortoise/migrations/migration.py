from __future__ import annotations

from tortoise.migrations.operations import Operation
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_generator.state import State
from tortoise.transactions import in_transaction


class Migration:
    operations: list[Operation] = []
    dependencies: list[tuple[str, str]] = []
    run_before: list[tuple[str, str]] = []
    replaces: list[tuple[str, str]] = []
    initial: bool | None = None
    atomic: bool = True

    def __init__(self, name: str, app_label: str):
        self.name = name
        self.app_label = app_label
        self.operations = list(self.__class__.operations)
        self.dependencies = list(self.__class__.dependencies)
        self.run_before = list(self.__class__.run_before)
        self.replaces = list(self.__class__.replaces)

    async def run_operations(
        self,
        app_label: str,
        state: State,
        *,
        dry_run: bool = False,
        schema_editor: BaseSchemaEditor | None = None,
    ) -> None:
        for operation in self.operations:
            await operation.run(app_label, state, dry_run, schema_editor)

    async def apply(
        self,
        state: State,
        *,
        dry_run: bool = False,
        schema_editor: BaseSchemaEditor | None = None,
        collect_sql: bool = False,
    ) -> State:
        supports_transactions = (
            schema_editor is not None and schema_editor.client.capabilities.supports_transactions
        )
        need_old_state = (collect_sql and schema_editor) or (
            not dry_run and schema_editor is not None
        )
        for operation in self.operations:
            old_state = state.clone() if need_old_state else None
            operation.state_forward(self.app_label, state)
            if collect_sql and schema_editor:
                schema_editor.collected_sql.append("--")
                schema_editor.collected_sql.append(f"-- {operation.describe()}")
                schema_editor.collected_sql.append("--")
                if not operation.reduces_to_sql:
                    schema_editor.collected_sql.append(
                        "-- THIS OPERATION CANNOT BE REPRESENTED AS SQL"
                    )
                    continue
                before = len(schema_editor.collected_sql)
                await self._run_database_forward(
                    operation,
                    old_state,  # type: ignore[arg-type]
                    state,
                    schema_editor,
                    supports_transactions,
                )
                if len(schema_editor.collected_sql) == before:
                    schema_editor.collected_sql.append("-- (no-op)")
                continue
            if dry_run or not schema_editor:
                continue
            await self._run_database_forward(
                operation,
                old_state,  # type: ignore[arg-type]
                state,
                schema_editor,
                supports_transactions,
            )
        state.validate_relations_initialized()
        return state

    async def unapply(
        self,
        state: State,
        *,
        dry_run: bool = False,
        schema_editor: BaseSchemaEditor | None = None,
        collect_sql: bool = False,
    ) -> State:
        supports_transactions = (
            schema_editor is not None and schema_editor.client.capabilities.supports_transactions
        )
        need_old_state = (collect_sql and schema_editor) or (
            not dry_run and schema_editor is not None
        )
        to_run: list[tuple[Operation, State, State]] = []
        new_state = state
        if not need_old_state and self.operations:
            # Single working copy so state_forward doesn't mutate the original
            new_state = state.clone()
        for operation in self.operations:
            if not getattr(operation, "reversible", True):
                raise ValueError(f"Operation {operation} in {self} is not reversible")
            if need_old_state:
                new_state = new_state.clone()
                old_state = new_state.clone()
                operation.state_forward(self.app_label, new_state)
                to_run.insert(0, (operation, old_state, new_state))
            else:
                operation.state_forward(self.app_label, new_state)

        for operation, to_state, from_state in to_run:
            if collect_sql and schema_editor:
                schema_editor.collected_sql.append("--")
                schema_editor.collected_sql.append(f"-- {operation.describe()}")
                schema_editor.collected_sql.append("--")
                if not operation.reduces_to_sql:
                    schema_editor.collected_sql.append(
                        "-- THIS OPERATION CANNOT BE REPRESENTED AS SQL"
                    )
                    continue
                before = len(schema_editor.collected_sql)
                await self._run_database_backward(
                    operation, from_state, to_state, schema_editor, supports_transactions
                )
                if len(schema_editor.collected_sql) == before:
                    schema_editor.collected_sql.append("-- (no-op)")
                continue
            if dry_run or not schema_editor:
                continue
            await self._run_database_backward(
                operation, from_state, to_state, schema_editor, supports_transactions
            )
        return state

    async def _run_database_forward(
        self,
        operation: Operation,
        old_state: State,
        new_state: State,
        schema_editor: BaseSchemaEditor,
        supports_transactions: bool,
    ) -> None:
        # Only wrap individual operations if schema editor is not already atomic.
        # Never wrap in a transaction when collecting SQL — no real DB needed.
        atomic_operation = operation.atomic or (self.atomic and operation.atomic is not False)
        if (
            not schema_editor.collect_sql
            and not schema_editor.atomic_migration
            and atomic_operation
            and supports_transactions
        ):
            async with in_transaction(schema_editor.client.connection_name):
                await operation.database_forward(
                    self.app_label, old_state, new_state, schema_editor
                )
        else:
            await operation.database_forward(self.app_label, old_state, new_state, schema_editor)

    async def _run_database_backward(
        self,
        operation: Operation,
        old_state: State,
        new_state: State,
        schema_editor: BaseSchemaEditor,
        supports_transactions: bool,
    ) -> None:
        # Only wrap individual operations if schema editor is not already atomic.
        # Never wrap in a transaction when collecting SQL — no real DB needed.
        atomic_operation = operation.atomic or (self.atomic and operation.atomic is not False)
        if (
            not schema_editor.collect_sql
            and not schema_editor.atomic_migration
            and atomic_operation
            and supports_transactions
        ):
            async with in_transaction(schema_editor.client.connection_name):
                await operation.database_backward(
                    self.app_label, old_state, new_state, schema_editor
                )
        else:
            await operation.database_backward(self.app_label, old_state, new_state, schema_editor)
