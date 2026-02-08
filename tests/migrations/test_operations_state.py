from __future__ import annotations

from typing import Any, cast

import pytest

from tortoise import fields
from tortoise.fields.relational import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
    RelationalField,
)
from tortoise.migrations.exceptions import IncompatibleStateError
from tortoise.migrations.operations import (
    AddField,
    AlterField,
    AlterModelOptions,
    CreateModel,
    DeleteModel,
    RemoveField,
    RenameModel,
)
from tortoise.migrations.schema_generator.state import State

RelationalFieldInstance = (
    ForeignKeyFieldInstance[Any] | OneToOneFieldInstance[Any] | ManyToManyFieldInstance[Any]
)


def test_add_model_only_id(empty_state: State):
    state = empty_state
    operation = CreateModel(name="TestModel", fields=[("id", fields.IntField(pk=True))])

    operation.state_forward("models", state)
    assert len(state.models) == 1
    assert len(state.apps.apps) == 1
    assert len(state.apps.apps["models"]) == 1

    model = state.apps.get_model("models.TestModel")
    assert isinstance(model._meta.pk, fields.IntField)


def test_add_model_simple_fields(empty_state: State):
    state = empty_state
    operation = CreateModel(
        name="TestModel",
        fields=[("id", fields.IntField(pk=True)), ("name", fields.TextField())],
    )
    operation.state_forward("models", state)

    model = state.apps.get_model("models.TestModel")
    assert len(model._meta.fields) == 2
    field = model._meta.fields_map["name"]
    assert isinstance(field, fields.TextField)
    model_state = state.models[("models", "TestModel")]

    assert len(model_state.fields) == 2


def test_add_model_two_simple_models_fields_in_one_app(empty_state: State):
    state = empty_state
    operation = CreateModel(
        name="TestModel",
        fields=[("id", fields.IntField(pk=True)), ("name", fields.TextField())],
    )
    operation.state_forward("models", state)

    operation = CreateModel(
        name="TestModel2",
        fields=[("id", fields.IntField(pk=True)), ("counter", fields.IntField())],
    )
    operation.state_forward("models", state)

    assert len(state.models) == 2
    assert len(state.apps.apps) == 1
    assert len(state.apps.apps["models"]) == 2


def test_add_model_two_simple_models_fields_in_two_apps(empty_state: State):
    state = empty_state
    operation = CreateModel(
        name="TestModel",
        fields=[("id", fields.IntField(pk=True)), ("name", fields.TextField())],
    )
    operation.state_forward("models", state)

    operation = CreateModel(
        name="TestModel2",
        fields=[("id", fields.IntField(pk=True)), ("counter", fields.IntField())],
    )
    operation.state_forward("models2", state)

    assert len(state.models) == 2
    assert len(state.apps.apps) == 2
    assert len(state.apps.apps["models"]) == 1
    assert len(state.apps.apps["models2"]) == 1


@pytest.mark.parametrize(
    ["field_class", "second_app", "models_in_second_app"],
    [
        (ForeignKeyFieldInstance, "models", 2),
        (ForeignKeyFieldInstance, "models2", 1),
        (OneToOneFieldInstance, "models", 2),
        (OneToOneFieldInstance, "models2", 1),
        (ManyToManyFieldInstance, "models", 2),
        (ManyToManyFieldInstance, "models2", 1),
    ],
)
def test_add_model_two_simple_models_fields_in_one_app_with_fk(
    empty_state: State,
    field_class: type[ForeignKeyFieldInstance | OneToOneFieldInstance | ManyToManyFieldInstance],
    second_app: str,
    models_in_second_app: int,
):
    state = empty_state
    operation = CreateModel(
        name="TestModel",
        fields=[("id", fields.IntField(pk=True)), ("name", fields.TextField())],
    )
    operation.state_forward("models", state)

    operation = CreateModel(
        name="TestModel2",
        fields=[
            ("id", fields.IntField(pk=True)),
            ("reference", field_class("models.TestModel", related_name="children")),
        ],
    )
    operation.state_forward(second_app, state)

    assert len(state.models) == 2
    assert len(state.apps.apps[second_app]) == models_in_second_app

    model2 = state.apps.get_model(f"{second_app}.TestModel2")
    fk_field = cast(RelationalFieldInstance, model2._meta.fields_map["reference"])
    assert isinstance(fk_field, field_class)
    assert fk_field.related_model.__name__ == "TestModel"


@pytest.mark.parametrize(
    "field_class",
    [ForeignKeyFieldInstance, OneToOneFieldInstance, ManyToManyFieldInstance],
)
def test_create_model_with_fk_to_not_yet_created_model(
    empty_state: State,
    field_class: type[ForeignKeyFieldInstance | OneToOneFieldInstance | ManyToManyFieldInstance],
):
    """Regression test: CreateModel should not raise when the FK target model
    hasn't been added to state yet (simulates alphabetical ordering where
    e.g. 'Event' is created before 'Tournament')."""
    state = empty_state

    # Create the model that references another model not yet in state.
    # This simulates alphabetical ordering: Alert (with FK to Warehouse) before Warehouse.
    op1 = CreateModel(
        name="Alert",
        fields=[
            ("id", fields.IntField(pk=True)),
            ("reference", field_class("models.Warehouse", related_name="alerts")),
        ],
    )
    op1.state_forward("models", state)

    # Now create the referenced model.
    op2 = CreateModel(
        name="Warehouse",
        fields=[
            ("id", fields.IntField(pk=True)),
            ("name", fields.TextField()),
        ],
    )
    op2.state_forward("models", state)

    assert len(state.models) == 2

    model_alert = state.apps.get_model("models.Alert")
    fk_field = cast(RelationalFieldInstance, model_alert._meta.fields_map["reference"])
    assert isinstance(fk_field, field_class)
    assert fk_field.related_model.__name__ == "Warehouse"

    # Validation should pass — all relations are resolved
    state.validate_relations_initialized()


def test_validate_catches_permanently_unresolved_relation(empty_state: State):
    """validate_relations_initialized should raise when a FK target model
    is never created, ensuring silent corruption cannot happen."""
    state = empty_state

    op = CreateModel(
        name="Orphan",
        fields=[
            ("id", fields.IntField(pk=True)),
            ("ref", ForeignKeyFieldInstance("models.Ghost", related_name="orphans")),
        ],
    )
    op.state_forward("models", state)

    with pytest.raises(RuntimeError, match="uninitialized relations"):
        state.validate_relations_initialized()


def test_simple_rename(state_with_model: State):
    operation = RenameModel("TestModel", "NewName")
    operation.state_forward("models", state_with_model)

    model_state = state_with_model.models[("models", "NewName")]
    assert model_state.name == "NewName"

    model = state_with_model.apps.get_model("models.NewName")
    assert model.__name__ == "NewName"


@pytest.mark.parametrize(
    ["field_class", "second_app"],
    [
        (ForeignKeyFieldInstance, "models"),
        (ForeignKeyFieldInstance, "models2"),
        (OneToOneFieldInstance, "models"),
        (OneToOneFieldInstance, "models2"),
        (ManyToManyFieldInstance, "models"),
        (ManyToManyFieldInstance, "models2"),
    ],
)
def test_rename_with_fk(
    state_with_model: State,
    field_class: type[ForeignKeyFieldInstance | OneToOneFieldInstance | ManyToManyFieldInstance],
    second_app: str,
):
    state = state_with_model
    operation = CreateModel(
        name="TestModel2",
        fields=[
            ("id", fields.IntField(pk=True)),
            ("reference", field_class("models.TestModel", related_name="children")),
        ],
    )
    operation.state_forward(second_app, state)

    operation = RenameModel("TestModel", "NewName")
    operation.state_forward("models", state)

    model_state = state.models[(second_app, "TestModel2")]
    field = cast(RelationalFieldInstance, model_state.fields["reference"])
    assert isinstance(field, field_class)
    assert field.model_name == "models.NewName"


def test_simple_delete_model(state_with_model: State):
    operation = DeleteModel("TestModel")
    operation.state_forward("models", state_with_model)

    assert ("models", "TestModel") not in state_with_model.models
    with pytest.raises(KeyError):
        state_with_model.apps.get_model("models.TestModel")


def test_delete_model_fail_on_refs(state_with_model: State):
    state = state_with_model
    operation = CreateModel(
        name="TestModel2",
        fields=[
            ("id", fields.IntField(pk=True)),
            (
                "reference",
                ForeignKeyFieldInstance("models.TestModel", related_name="children"),
            ),
        ],
    )
    operation.state_forward("models", state)

    operation = DeleteModel("TestModel")
    with pytest.raises(IncompatibleStateError):
        operation.state_forward("models", state_with_model)


def test_alter_options(state_with_model: State):
    operation = AlterModelOptions(name="TestModel", options={"ordering": ["-id"]})
    operation.state_forward("models", state_with_model)

    model_state = state_with_model.models[("models", "TestModel")]
    assert model_state.options["ordering"] == ["-id"]


def test_add_field(state_with_model: State):
    operation = AddField(model_name="TestModel", name="name", field=fields.TextField())
    operation.state_forward("models", state_with_model)

    model_state = state_with_model.models[("models", "TestModel")]
    assert isinstance(model_state.fields["name"], fields.TextField)

    model = state_with_model.apps.get_model("models.TestModel")
    assert isinstance(model._meta.fields_map.get("name"), fields.TextField)


@pytest.mark.parametrize(
    ["field_class", "backward_field_class"],
    [
        (ForeignKeyFieldInstance, BackwardFKRelation),
        (ManyToManyFieldInstance, ManyToManyFieldInstance),
        (OneToOneFieldInstance, BackwardOneToOneRelation),
    ],
)
def test_add_field_relational(
    state_with_two_models: State,
    field_class: type[ForeignKeyFieldInstance | OneToOneFieldInstance | ManyToManyFieldInstance],
    backward_field_class: type[
        BackwardFKRelation | BackwardOneToOneRelation | ManyToManyFieldInstance
    ],
):
    state = state_with_two_models

    operation = AddField(
        model_name="TestModel2",
        name="ref",
        field=field_class("models.TestModel", related_name="child"),
    )
    operation.state_forward("models", state)

    model_state = state.models["models", "TestModel2"]
    field = cast(RelationalFieldInstance, model_state.fields["ref"])
    assert isinstance(field, field_class)
    assert field.model_name == "models.TestModel"

    model = state.apps.get_model("models.TestModel")
    model2 = state.apps.get_model("models.TestModel2")
    field_on_model = cast(RelationalField, model2._meta.fields_map["ref"])
    assert field_on_model.related_model == model

    backward_field = model._meta.fields_map["child"]
    assert isinstance(backward_field, backward_field_class)


def test_remove_field(state_with_model: State):
    operation = AddField(model_name="TestModel", name="name", field=fields.TextField())
    operation.state_forward("models", state_with_model)

    operation = RemoveField(model_name="TestModel", name="name")
    operation.state_forward("models", state_with_model)

    model_state = state_with_model.models[("models", "TestModel")]
    assert not model_state.fields.get("name")

    model = state_with_model.apps.get_model("models.TestModel")
    assert not model._meta.fields_map.get("name")


@pytest.mark.parametrize(
    "field_class",
    [ForeignKeyFieldInstance, ManyToManyFieldInstance, OneToOneFieldInstance],
)
def test_remove_field_relational(
    state_with_two_models: State,
    field_class: type[ForeignKeyFieldInstance | OneToOneFieldInstance | ManyToManyFieldInstance],
):
    state = state_with_two_models

    operation = AddField(
        model_name="TestModel2",
        name="ref",
        field=field_class("models.TestModel", related_name="child"),
    )
    operation.state_forward("models", state)

    operation = RemoveField(
        model_name="TestModel2",
        name="ref",
    )
    operation.state_forward("models", state)
    assert not state.models["models", "TestModel2"].fields.get("ref")

    model = state.apps.get_model("models.TestModel")
    model2 = state.apps.get_model("models.TestModel2")
    assert not model2._meta.fields_map.get("ref")
    assert not model._meta.fields_map.get("child")


def test_alter_field(state_with_model: State):
    operation = AddField(
        model_name="TestModel", name="name", field=fields.CharField(max_length=255)
    )
    operation.state_forward("models", state_with_model)

    operation = AlterField(
        model_name="TestModel",
        name="name",
        field=fields.CharField(max_length=255, unique=True),
    )
    operation.state_forward("models", state_with_model)

    model_state = state_with_model.models[("models", "TestModel")]
    assert model_state.fields["name"].unique

    model = state_with_model.apps.get_model("models.TestModel")
    assert model._meta.fields_map["name"].unique
