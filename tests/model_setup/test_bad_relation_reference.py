import pytest

from tortoise import Tortoise
from tortoise.context import _current_context
from tortoise.exceptions import ConfigurationError

# Save original classproperties before any test can shadow them
_original_apps_prop = Tortoise.__dict__["apps"]
_original_inited_prop = Tortoise.__dict__["_inited"]


async def _reset_tortoise():
    """Helper to reset Tortoise state before each test.

    Note: We MUST NOT set Tortoise.apps = None or Tortoise._inited = False
    because these are classproperties and setting them shadows the property
    with a class attribute, breaking future access.
    """
    # Restore original classproperties if they were shadowed
    if not isinstance(Tortoise.__dict__.get("apps"), type(_original_apps_prop)):
        type.__setattr__(Tortoise, "apps", _original_apps_prop)
    if not isinstance(Tortoise.__dict__.get("_inited"), type(_original_inited_prop)):
        type.__setattr__(Tortoise, "_inited", _original_inited_prop)

    # Get this test's own context (NOT the global fallback)
    ctx = _current_context.get()
    if ctx is not None:
        if ctx._connections is not None:
            ctx._connections._storage.clear()
            ctx._connections._db_config = None
            ctx._connections = None
        ctx._apps = None
        ctx._inited = False
        ctx._default_connection = None


async def _teardown_tortoise():
    """Helper to teardown Tortoise state after each test."""
    ctx = _current_context.get()
    if ctx is not None and ctx._apps is not None:
        for model in ctx._apps.get_models_iterable():
            model._meta.default_connection = None
        ctx._apps.clear()
        ctx._apps = None


@pytest.mark.asyncio
async def test_wrong_app_init():
    await _reset_tortoise()
    try:
        with pytest.raises(ConfigurationError, match="No app with name 'app' registered."):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel1"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_wrong_model_init():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match="No model with name 'Tour' registered in app 'models'."
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel2"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_no_app_in_reference_init():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='ForeignKeyField accepts model name in format "app.Model"'
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel3"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_more_than_two_dots_in_reference_init():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='ForeignKeyField accepts model name in format "app.Model"'
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel4"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_no_app_in_o2o_reference_init():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='OneToOneField accepts model name in format "app.Model"'
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel5"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_non_unique_field_in_fk_reference_init():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='field "uuid" in model "Tournament" is not unique'
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel6"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_non_exist_field_in_fk_reference_init():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='there is no field named "uuids" in model "Tournament"'
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel7"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_non_unique_field_in_o2o_reference_init():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='field "uuid" in model "Tournament" is not unique'
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel8"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()


@pytest.mark.asyncio
async def test_non_exist_field_in_o2o_reference_init():
    await _reset_tortoise()
    try:
        with pytest.raises(
            ConfigurationError, match='there is no field named "uuids" in model "Tournament"'
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tests.model_setup.model_bad_rel9"],
                            "default_connection": "default",
                        }
                    },
                }
            )
    finally:
        await _teardown_tortoise()
