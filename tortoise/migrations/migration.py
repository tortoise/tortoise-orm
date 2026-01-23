from __future__ import annotations

from typing import List

from tortoise.migrations.operations import Operation
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_generator.state import State


class Migration:
    operations: List[Operation] = []

    def __init__(self, name: str):
        self.name = name

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
