import pytest

from tortoise import fields
from tortoise.migrations.operations import CreateModel
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps


@pytest.fixture(scope="session", autouse=True)
def initialize_tests():
    # TODO merge these tests in main tests directory
    return None


@pytest.fixture
def empty_state() -> State:
    return State(models={}, apps=StateApps())


@pytest.fixture
def state_with_model(empty_state: State) -> State:
    CreateModel(name="TestModel", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", empty_state
    )
    return empty_state


@pytest.fixture
def state_with_two_models(empty_state: State) -> State:
    CreateModel(name="TestModel", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", empty_state
    )
    CreateModel(name="TestModel2", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", empty_state
    )
    return empty_state
