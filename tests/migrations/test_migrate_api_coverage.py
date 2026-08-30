import sys
from types import ModuleType

import pytest

from tortoise import Tortoise, fields, models
from tortoise.migrations.api import migrate, plan


class DummyModel(models.Model):
    id = fields.IntField(pk=True)

    class Meta:
        app = "app_c"


class DummyModelD(models.Model):
    id = fields.IntField(pk=True)

    class Meta:
        app = "app_d"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    sys.modules.pop("test_mod_c", None)
    sys.modules.pop("test_mod_d", None)


@pytest.mark.asyncio
async def test_migrate_api_executor_targets_empty(tmp_path):
    mod_c = ModuleType("test_mod_c")
    mod_c.DummyModel = DummyModel
    sys.modules["test_mod_c"] = mod_c

    mod_d = ModuleType("test_mod_d")
    mod_d.DummyModelD = DummyModelD
    sys.modules["test_mod_d"] = mod_d

    config = {
        "connections": {"default": "sqlite://:memory:", "other": "sqlite://:memory:"},
        "apps": {
            "app_c": {"models": ["test_mod_c"], "default_connection": "default"},
            "app_d": {"models": ["test_mod_d"], "default_connection": "other"},
        },
    }

    # Pass app_labels=["app_c"] so for "other" connection, executor_targets will be empty.
    # We use migrate and check it doesn't crash on the 'other' connection loop iteration.
    try:
        await migrate(config=config, app_labels=["app_c"])
    finally:
        await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_plan_api_executor_targets_empty(tmp_path):
    mod_c = ModuleType("test_mod_c")
    mod_c.DummyModel = DummyModel
    sys.modules["test_mod_c"] = mod_c

    mod_d = ModuleType("test_mod_d")
    mod_d.DummyModelD = DummyModelD
    sys.modules["test_mod_d"] = mod_d

    config = {
        "connections": {"default": "sqlite://:memory:", "other": "sqlite://:memory:"},
        "apps": {
            "app_c": {"models": ["test_mod_c"], "default_connection": "default"},
            "app_d": {"models": ["test_mod_d"], "default_connection": "other"},
        },
    }

    # Test the plan API, covering the empty executor_targets case (lines 47-48)
    # and plan missing lines in general.
    try:
        output = await plan(config=config, app_labels=["app_c"])
        # The output shouldn't have 'other' connection steps.
        # But wait, there are no migrations, so it should be empty list?
        # plan() runs executor.plan() which returns list of PlanStep.
        # Since we have no migrations, output should just be `# Connection: default` ?
        assert any("Connection: default" in line for line in output)
        assert not any("Connection: other" in line for line in output)
    finally:
        await Tortoise.close_connections()

@pytest.mark.asyncio
async def test_plan_api_all_targets(tmp_path):
    mod_c = ModuleType("test_mod_c")
    mod_c.DummyModel = DummyModel
    sys.modules["test_mod_c"] = mod_c

    mod_d = ModuleType("test_mod_d")
    mod_d.DummyModelD = DummyModelD
    sys.modules["test_mod_d"] = mod_d

    config = {
        "connections": {"default": "sqlite://:memory:", "other": "sqlite://:memory:"},
        "apps": {
            "app_c": {"models": ["test_mod_c"], "default_connection": "default"},
            "app_d": {"models": ["test_mod_d"], "default_connection": "other"},
        },
    }

    try:
        output = await plan(config=config)
        assert any("Connection: default" in line for line in output)
        assert any("Connection: other" in line for line in output)
    finally:
        await Tortoise.close_connections()
