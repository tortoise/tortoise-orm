from __future__ import annotations

from typing import Any

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.fields.base import Field
from tortoise.indexes import Index
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.operations import (
    AddConstraint,
    AddField,
    AddIndex,
    AlterField,
    CreateModel,
    DeleteModel,
    RemoveIndex,
    RenameConstraint,
    RenameIndex,
    RunPython,
)
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_generator.state import ModelState, State
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


class TestSchemaEditor(BaseSchemaEditor):
    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return ""

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return ""


def make_model(
    model_name: str,
    *,
    meta_options: dict[str, Any] | None = None,
    **model_fields: Field,
) -> type[Model]:
    attrs: dict[str, Any] = dict(model_fields)
    options: dict[str, Any] = {"app": "models", "table": "widget"}
    if meta_options:
        options.update(meta_options)
    attrs["Meta"] = type("Meta", (), options)
    return type(model_name, (Model,), attrs)


def build_state(app_label: str, model: type) -> State:
    apps = StateApps()
    state = State(models={}, apps=apps)
    model_state = ModelState.make_from_model(app_label, model)
    state.models[(app_label, model.__name__)] = model_state
    model_clone = model_state.render(apps)
    apps.register_model(app_label, model_clone)
    return state


@pytest.mark.asyncio
async def test_create_model_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())

    op = CreateModel(
        name="Widget",
        fields=[("id", fields.IntField(pk=True)), ("name", fields.TextField())],
    )

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert client.executed
    assert 'CREATE TABLE "widget"' in client.executed[0]


@pytest.mark.asyncio
async def test_add_field_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = AddField(model_name="Widget", name="name", field=fields.TextField())

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert client.executed
    assert 'ALTER TABLE "widget" ADD COLUMN' in client.executed[0]


@pytest.mark.asyncio
async def test_delete_model_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = DeleteModel(name="Widget")

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert client.executed
    assert 'DROP TABLE "widget"' in client.executed[0]


@pytest.mark.asyncio
async def test_add_index_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = AddIndex(
        model_name="Widget",
        index=Index(fields=("id",), name="idx_widget_id"),
    )

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert client.executed
    assert 'CREATE INDEX "idx_widget_id"' in client.executed[0]


@pytest.mark.asyncio
async def test_remove_index_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )
    AddIndex(
        model_name="Widget",
        index=Index(fields=("id",), name="idx_widget_id"),
    ).state_forward("models", state)

    op = RemoveIndex(model_name="Widget", name="idx_widget_id")

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert client.executed
    assert 'DROP INDEX "idx_widget_id"' in client.executed[0]


@pytest.mark.asyncio
async def test_rename_index_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )
    AddIndex(
        model_name="Widget",
        index=Index(fields=("id",), name="idx_widget_id"),
    ).state_forward("models", state)

    op = RenameIndex(model_name="Widget", old_name="idx_widget_id", new_name="idx_widget_id_new")

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert client.executed
    assert 'ALTER INDEX "idx_widget_id" RENAME TO "idx_widget_id_new"' in client.executed[0]


@pytest.mark.asyncio
async def test_add_constraint_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = AddConstraint(
        model_name="Widget",
        constraint=UniqueConstraint(fields=("id",), name="uniq_widget_id"),
    )

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert client.executed
    assert (
        'ALTER TABLE "widget" ADD CONSTRAINT "uniq_widget_id" UNIQUE ("id")' in client.executed[0]
    )


@pytest.mark.asyncio
async def test_alter_field_backward_renames_columns() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    OldWidget = make_model(
        "Widget",
        id=fields.IntField(pk=True),
        body=fields.TextField(),
    )
    NewWidget = make_model(
        "Widget",
        id=fields.IntField(pk=True),
        body=fields.TextField(source_field="content"),
    )

    old_state = build_state("models", NewWidget)
    new_state = build_state("models", OldWidget)

    op = AlterField(model_name="Widget", name="body", field=fields.TextField())

    await op.database_backward("models", old_state, new_state, state_editor=editor)

    assert client.executed
    assert 'RENAME COLUMN "content" TO "body"' in client.executed[0]


@pytest.mark.asyncio
async def test_run_python_operation_runs_callable() -> None:
    calls: list[tuple[StateApps, BaseSchemaEditor]] = []
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    model = make_model("Widget", id=fields.IntField(pk=True))
    state = build_state("models", model)

    def forward(apps: StateApps, schema_editor: BaseSchemaEditor) -> None:
        apps.get_model("models.Widget")
        calls.append((apps, schema_editor))

    op = RunPython(forward)

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(calls) == 1
    apps, schema_editor = calls[0]
    assert schema_editor is editor
    apps.get_model("models.Widget")


@pytest.mark.asyncio
async def test_rename_constraint_backward_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    model = make_model("Widget", id=fields.IntField(pk=True))
    state = build_state("models", model)

    op = RenameConstraint(model_name="Widget", old_name="uniq_old", new_name="uniq_new")

    await op.database_backward("models", state, state, state_editor=editor)

    assert client.executed
    assert 'RENAME CONSTRAINT "uniq_new" TO "uniq_old"' in client.executed[0]
