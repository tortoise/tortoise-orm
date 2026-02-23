from __future__ import annotations

import time
from typing import Any
from unittest.mock import patch

import pytest

from tortoise import fields
from tortoise.fields.relational import ForeignKeyFieldInstance
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


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_state_building_performance_200_models():
    """State building from 200 CreateModel operations must complete quickly."""
    migrations = _build_migrations(200)
    state = State(models={}, apps=StateApps())

    t0 = time.perf_counter()
    for migration in migrations:
        await migration.apply(state, dry_run=True, schema_editor=None)
    elapsed = time.perf_counter() - t0

    assert len(state.models) == 200
    print(f"\nState building: {elapsed * 1000:.1f}ms ({elapsed / 200 * 1000:.2f}ms/model)")
    assert elapsed < 2.0, f"State building took {elapsed:.1f}s, expected < 2s"


@pytest.mark.asyncio
async def test_apply_dry_run_does_not_clone_state():
    """Verify that apply(dry_run=True) never calls State.clone()."""
    migrations = _build_migrations(10)
    state = State(models={}, apps=StateApps())

    clone_calls = 0
    original_clone = State.clone

    def counting_clone(self):
        nonlocal clone_calls
        clone_calls += 1
        return original_clone(self)

    with patch.object(State, "clone", counting_clone):
        for migration in migrations:
            await migration.apply(state, dry_run=True, schema_editor=None)

    assert len(state.models) == 10
    assert clone_calls == 0, f"State.clone() was called {clone_calls} times during dry_run"


def test_state_clone_produces_independent_copy():
    """Cloned state must be fully independent from the original."""
    state = State(models={}, apps=StateApps())
    for i in range(50):
        field_list: list[tuple[str, Any]] = [
            ("id", fields.IntField(primary_key=True)),
            ("name", fields.CharField(max_length=255)),
        ]
        if i > 0 and i % 5 == 0:
            field_list.append(
                ("ref", fields.ForeignKeyField(f"app.Model{i - 1}", related_name=f"ch_{i}")),
            )
        op = CreateModel(name=f"Model{i}", fields=field_list, options={"table": f"model_{i}"})
        op.state_forward("app", state)

    cloned = state.clone()

    # Mutate a field on the clone
    key = ("app", "Model0")
    cloned_field = cloned.models[key].fields["name"]
    cloned_field.max_length = 999

    # Original must be unaffected
    original_field = state.models[key].fields["name"]
    assert original_field.max_length == 255

    # Add a model to the clone
    extra_op = CreateModel(
        name="ExtraModel",
        fields=[("id", fields.IntField(primary_key=True))],
    )
    extra_op.state_forward("app", cloned)

    assert ("app", "ExtraModel") in cloned.models
    assert ("app", "ExtraModel") not in state.models


def test_state_clone_preserves_relations():
    """Cloned state must have functional FK relations."""
    state = State(models={}, apps=StateApps())
    CreateModel(
        name="Parent",
        fields=[("id", fields.IntField(primary_key=True))],
        options={"table": "parent"},
    ).state_forward("app", state)
    CreateModel(
        name="Child",
        fields=[
            ("id", fields.IntField(primary_key=True)),
            ("parent", fields.ForeignKeyField("app.Parent", related_name="children")),
        ],
        options={"table": "child"},
    ).state_forward("app", state)

    cloned = state.clone()

    parent_model = cloned.apps.get_model("app", "Parent")
    child_model = cloned.apps.get_model("app", "Child")

    fk = child_model._meta.fields_map["parent"]
    assert isinstance(fk, ForeignKeyFieldInstance)
    assert fk.related_model is parent_model
