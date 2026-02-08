"""Benchmark for migration state building performance.

Exercises State.apply() over 200 CreateModel operations (every 3rd with FK).
"""

import asyncio
from typing import Any

from tortoise import fields
from tortoise.migrations.migration import Migration
from tortoise.migrations.operations import CreateModel, Operation
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps


def _make_create_model_op(i: int) -> CreateModel:
    field_list: list[tuple[str, Any]] = [
        ("id", fields.IntField(primary_key=True)),
        ("name", fields.CharField(max_length=255)),
        ("description", fields.TextField(null=True)),
        ("created_at", fields.DatetimeField(auto_now_add=True)),
        ("updated_at", fields.DatetimeField(auto_now=True)),
        ("is_active", fields.BooleanField(default=True)),
        ("sort_order", fields.IntField(default=0)),
    ]
    if i > 0 and i % 3 == 0:
        field_list.append(
            ("parent", fields.ForeignKeyField(f"app.Model{i - 1}", related_name=f"ch_{i}")),
        )
    return CreateModel(name=f"Model{i}", fields=field_list, options={"table": f"model_{i}"})


def _build_migrations(num_models: int, batch_size: int = 20) -> list[Migration]:
    all_ops: list[Operation] = [_make_create_model_op(i) for i in range(num_models)]
    migrations: list[Migration] = []
    for start in range(0, len(all_ops), batch_size):
        batch = all_ops[start : start + batch_size]

        class Mig(Migration):
            pass

        Mig.operations = batch
        migrations.append(Mig(name=f"mig_{start // batch_size:04d}", app_label="app"))
    return migrations


def test_state_building_200_models(benchmark):
    """State building from 200 CreateModel operations with FK relations."""
    loop = asyncio.get_event_loop()
    migrations = _build_migrations(200)

    @benchmark
    def bench():
        async def _bench():
            state = State(models={}, apps=StateApps())
            for migration in migrations:
                await migration.apply(state, dry_run=True, schema_editor=None)
            assert len(state.models) == 200

        loop.run_until_complete(_bench())
