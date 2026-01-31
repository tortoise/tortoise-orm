from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from tortoise import fields
from tortoise.contrib.postgres.fields import TSVectorField
from tortoise.contrib.postgres.indexes import GinIndex
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
    RemoveConstraint,
    RemoveField,
    RemoveIndex,
    RenameConstraint,
    RenameField,
    RenameIndex,
    RenameModel,
)
from tortoise.migrations.schema_generator.operation_generator import OperationGenerator
from tortoise.migrations.schema_generator.state import ModelState, State
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


def build_state(app_label: str, *models: type[Model]) -> State:
    state = State(models={}, apps=StateApps())
    for model in models:
        state.models[(app_label, model.__name__)] = ModelState.make_from_model(app_label, model)
    return state


def make_model(
    model_name: str,
    table: str,
    meta_options: Mapping[str, Any] | None = None,
    /,
    **model_fields: Field,
) -> type[Model]:
    attrs: dict[str, Any] = dict(model_fields)
    options: dict[str, Any] = {"app": "models", "table": table}
    if meta_options:
        options.update(meta_options)
    meta = type("Meta", (), options)
    attrs["Meta"] = meta
    return type(model_name, (Model,), attrs)


def make_text_field(source_field: str | None) -> fields.TextField:
    if source_field is None:
        return fields.TextField()
    return fields.TextField(source_field=source_field)


def test_generate_create_and_delete_model() -> None:
    Widget = make_model("Widget", "widget", id=fields.IntField(pk=True), name=fields.TextField())

    old_state = build_state("models")
    new_state = build_state("models", Widget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert len(operations) == 1
    assert isinstance(operations[0], CreateModel)

    operations = OperationGenerator(new_state, old_state).generate()
    assert len(operations) == 1
    assert isinstance(operations[0], DeleteModel)


def test_generate_rename_model_heuristic() -> None:
    OldWidget = make_model(
        "OldWidget", "widget", id=fields.IntField(pk=True), name=fields.TextField()
    )
    NewWidget = make_model(
        "NewWidget", "widget", id=fields.IntField(pk=True), name=fields.TextField()
    )

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert len(operations) == 1
    assert isinstance(operations[0], RenameModel)


def test_generate_field_ops() -> None:
    OldWidget = make_model("Widget", "widget", id=fields.IntField(pk=True), name=fields.TextField())
    NewWidget = make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        title=fields.TextField(source_field="name"),
        age=fields.IntField(),
    )

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, RenameField) for op in operations)
    assert any(isinstance(op, AddField) for op in operations)


@pytest.mark.parametrize(
    ("old_name", "new_name", "old_source", "new_source", "expect_rename", "expect_alter"),
    [
        ("title", "title", None, None, False, False),
        ("title", "title", None, "legacy_title", False, True),
        ("title", "headline", None, None, True, False),
        ("title", "headline", None, "title", True, False),
    ],
)
def test_generate_rename_field_source_field_matrix(
    old_name: str,
    new_name: str,
    old_source: str | None,
    new_source: str | None,
    expect_rename: bool,
    expect_alter: bool,
) -> None:
    OldWidget = make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        **{old_name: make_text_field(old_source)},
    )
    NewWidget = make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        **{new_name: make_text_field(new_source)},
    )

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, RenameField) for op in operations) is expect_rename
    assert any(isinstance(op, AlterField) for op in operations) is expect_alter


def test_generate_alter_field() -> None:
    OldWidget = make_model("Widget", "widget", id=fields.IntField(pk=True), name=fields.TextField())
    NewWidget = make_model(
        "Widget", "widget", id=fields.IntField(pk=True), name=fields.TextField(null=True)
    )

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, AlterField) for op in operations)


def test_generate_alter_field_when_generated_sql_changes() -> None:
    OldWidget = make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        title=fields.TextField(),
        body=fields.TextField(),
        search_vector=TSVectorField(source_fields=("title",), config="english"),
    )
    NewWidget = make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        title=fields.TextField(),
        body=fields.TextField(),
        search_vector=TSVectorField(source_fields=("title", "body"), config="english"),
    )

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, RemoveField) for op in operations)
    assert any(isinstance(op, AddField) for op in operations)


def test_generate_recreate_generated_field_restores_indexes_constraints() -> None:
    OldWidget = make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        title=fields.TextField(),
        body=fields.TextField(),
        search_vector=TSVectorField(source_fields=("title",), config="english", index=True),
    )
    NewWidget = make_model(
        "Widget",
        "widget",
        id=fields.IntField(pk=True),
        title=fields.TextField(),
        body=fields.TextField(),
        search_vector=TSVectorField(source_fields=("title", "body"), config="english", index=True),
    )
    OldWidget._meta.indexes = (GinIndex(fields=("search_vector",)),)
    OldWidget._meta.unique_together = (("title", "search_vector"),)
    NewWidget._meta.indexes = (GinIndex(fields=("search_vector",)),)
    NewWidget._meta.unique_together = (("title", "search_vector"),)

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, RemoveField) for op in operations)
    assert any(isinstance(op, AddField) for op in operations)
    assert any(isinstance(op, AddIndex) and op.index.INDEX_TYPE == "GIN" for op in operations)
    assert any(
        isinstance(op, AddConstraint) and op.constraint.fields == ("title", "search_vector")
        for op in operations
    )


def test_generate_add_remove_index() -> None:
    OldWidget = make_model("Widget", "widget", id=fields.IntField(pk=True), name=fields.TextField())
    NewWidget = make_model(
        "Widget",
        "widget",
        {"indexes": (("name",),)},
        id=fields.IntField(pk=True),
        name=fields.TextField(),
    )

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, AddIndex) for op in operations)

    operations = OperationGenerator(new_state, old_state).generate()
    assert any(isinstance(op, RemoveIndex) for op in operations)


def test_generate_rename_index_explicit() -> None:
    OldWidget = make_model(
        "Widget",
        "widget",
        {"indexes": (Index(fields=("name",), name="idx_old"),)},
        id=fields.IntField(pk=True),
        name=fields.TextField(),
    )
    NewWidget = make_model(
        "Widget",
        "widget",
        {"indexes": (Index(fields=("name",), name="idx_new"),)},
        id=fields.IntField(pk=True),
        name=fields.TextField(),
    )

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, RenameIndex) for op in operations)


def test_generate_unique_together_constraints() -> None:
    OldWidget = make_model(
        "Widget",
        "widget",
        {"unique_together": (("name", "age"),)},
        id=fields.IntField(pk=True),
        name=fields.TextField(),
        age=fields.IntField(),
    )
    NewWidget = make_model(
        "Widget",
        "widget",
        {"unique_together": (("name",),)},
        id=fields.IntField(pk=True),
        name=fields.TextField(),
        age=fields.IntField(),
    )

    old_state = build_state("models", OldWidget)
    new_state = build_state("models", NewWidget)

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, RemoveConstraint) for op in operations)
    assert any(isinstance(op, AddConstraint) for op in operations)


def test_generate_rename_constraint_explicit() -> None:
    Widget = make_model("Widget", "widget", id=fields.IntField(pk=True), name=fields.TextField())

    old_state = build_state("models", Widget)
    new_state = build_state("models", Widget)

    old_state.models[("models", "Widget")].options["constraints"] = (
        UniqueConstraint(fields=("name",), name="uq_old"),
    )
    new_state.models[("models", "Widget")].options["constraints"] = (
        UniqueConstraint(fields=("name",), name="uq_new"),
    )

    operations = OperationGenerator(old_state, new_state).generate()
    assert any(isinstance(op, RenameConstraint) for op in operations)
