import pytest

from tortoise import fields
from tortoise.migrations.operations import CreateModel
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps


@pytest.fixture
def empty_state() -> State:
    return State(models={}, apps=StateApps())


@pytest.fixture
def state_with_model() -> State:
    state = State(models={}, apps=StateApps())
    operation = CreateModel(
        name="TestModel",
        fields=[("id", fields.IntField(pk=True))],
    )

    operation.state_forward("models", state)
    return state


@pytest.fixture
def state_with_two_models(state_with_model):
    operation = CreateModel(
        name="TestModel2",
        fields=[("id", fields.IntField(pk=True)), ("counter", fields.IntField())],
    )
    operation.state_forward("models", state_with_model)
    return state_with_model


@pytest.fixture
def state_with_two_related_models(state_with_model):
    operation = CreateModel(
        name="TestModel2",
        fields=[("id", fields.IntField(pk=True)), ("ref", fields.IntField())],
    )
    operation.state_forward("models", state_with_model)
    return state_with_model
