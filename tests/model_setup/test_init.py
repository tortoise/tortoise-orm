import os
from unittest.mock import patch

import pytest

from tortoise import Tortoise, connections
from tortoise.config import AppConfig, ConnectionConfig, TortoiseConfig
from tortoise.context import TortoiseContext, get_current_context
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

    # Get the current context and properly reset it
    ctx = get_current_context()
    if ctx is not None:
        # Clear db_config first to prevent close_all from trying to import bad backends
        if ctx._connections is not None:
            # Clear storage without closing (to avoid importing bad backends)
            ctx._connections._storage.clear()
            ctx._connections._db_config = None
            ctx._connections = None
        ctx._apps = None
        ctx._inited = False
        ctx._default_connection = None
    else:
        # No context exists - create one for the test
        ctx = TortoiseContext()
        ctx.__enter__()


@pytest.mark.asyncio
async def test_basic_init():
    await _reset_tortoise()
    await Tortoise.init(
        {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": ":memory:"},
                }
            },
            "apps": {"models": {"models": ["tests.testmodels"], "default_connection": "default"}},
        }
    )
    assert "models" in Tortoise.apps
    assert connections.get("default") is not None


@pytest.mark.asyncio
async def test_dataclass_init():
    await _reset_tortoise()
    await Tortoise.init(
        config=TortoiseConfig(
            connections={
                "default": ConnectionConfig(
                    engine="tortoise.backends.sqlite",
                    credentials={"file_path": ":memory:"},
                )
            },
            apps={
                "models": AppConfig(
                    models=["tests.testmodels"],
                    default_connection="default",
                )
            },
        )
    )
    assert "models" in Tortoise.apps
    assert connections.get("default") is not None


@pytest.mark.asyncio
async def test_empty_modules_init():
    await _reset_tortoise()
    with pytest.warns(RuntimeWarning, match='Module "tests.model_setup" has no models'):
        await Tortoise.init(
            {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.sqlite",
                        "credentials": {"file_path": ":memory:"},
                    }
                },
                "apps": {
                    "models": {"models": ["tests.model_setup"], "default_connection": "default"}
                },
            }
        )


@pytest.mark.asyncio
async def test_dup1_init():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError, match='backward relation "events" duplicates in model Tournament'
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
                        "models": ["tests.model_setup.models_dup1"],
                        "default_connection": "default",
                    }
                },
            }
        )


@pytest.mark.asyncio
async def test_dup2_init():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError, match='backward relation "events" duplicates in model Team'
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
                        "models": ["tests.model_setup.models_dup2"],
                        "default_connection": "default",
                    }
                },
            }
        )


@pytest.mark.asyncio
async def test_dup3_init():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError, match='backward relation "event" duplicates in model Tournament'
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
                        "models": ["tests.model_setup.models_dup3"],
                        "default_connection": "default",
                    }
                },
            }
        )


@pytest.mark.asyncio
async def test_generated_nonint():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError, match="Field 'val' \\(CharField\\) can't be DB-generated"
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
                        "models": ["tests.model_setup.model_generated_nonint"],
                        "default_connection": "default",
                    }
                },
            }
        )


@pytest.mark.asyncio
async def test_multiple_pk():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError,
        match="Can't create model Tournament with two primary keys, only single primary key is supported",
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
                        "models": ["tests.model_setup.model_multiple_pk"],
                        "default_connection": "default",
                    }
                },
            }
        )


@pytest.mark.asyncio
async def test_nonpk_id():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError,
        match="Can't create model Tournament without explicit primary key if"
        " field 'id' already present",
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
                        "models": ["tests.model_setup.model_nonpk_id"],
                        "default_connection": "default",
                    }
                },
            }
        )


@pytest.mark.asyncio
async def test_unknown_connection():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError,
        match='App "models" refers to unknown connection "fioop"',
    ):
        await Tortoise.init(
            {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.sqlite",
                        "credentials": {"file_path": ":memory:"},
                    }
                },
                "apps": {"models": {"models": ["tests.testmodels"], "default_connection": "fioop"}},
            }
        )


@pytest.mark.asyncio
async def test_init_connections_false():
    await _reset_tortoise()
    config = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.sqlite",
                "credentials": {"file_path": ":memory:"},
            }
        },
        "apps": {"models": {"models": ["tests.testmodels"], "default_connection": "default"}},
    }
    with (
        patch("tortoise.connections._init") as mocked_init,
        patch("tortoise.connections.get") as mocked_get,
    ):
        await Tortoise.init(config=config, init_connections=False)
        mocked_init.assert_not_called()
        mocked_get.assert_not_called()
    assert "models" in Tortoise.apps
    assert connections.db_config == config["connections"]


@pytest.mark.asyncio
async def test_init_connections_false_with_create_db():
    await _reset_tortoise()
    config = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.sqlite",
                "credentials": {"file_path": ":memory:"},
            }
        },
        "apps": {"models": {"models": ["tests.testmodels"], "default_connection": "default"}},
    }
    with pytest.raises(
        ConfigurationError, match="init_connections=False cannot be used with _create_db=True"
    ):
        await Tortoise.init(config=config, _create_db=True, init_connections=False)


@pytest.mark.asyncio
async def test_url_without_modules():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError,
        match="Must provide either 'config', 'config_file', or both 'db_url' and 'modules'",
    ):
        await Tortoise.init(db_url=f"sqlite://{':memory:'}")


@pytest.mark.asyncio
async def test_default_connection_init():
    await _reset_tortoise()
    await Tortoise.init(
        {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": ":memory:"},
                }
            },
            "apps": {"models": {"models": ["tests.testmodels"]}},
        }
    )
    assert "models" in Tortoise.apps
    assert connections.get("default") is not None


@pytest.mark.asyncio
async def test_db_url_init():
    await _reset_tortoise()
    await Tortoise.init(
        {
            "connections": {"default": f"sqlite://{':memory:'}"},
            "apps": {"models": {"models": ["tests.testmodels"], "default_connection": "default"}},
        }
    )
    assert "models" in Tortoise.apps
    assert connections.get("default") is not None


@pytest.mark.asyncio
async def test_shorthand_init():
    await _reset_tortoise()
    await Tortoise.init(db_url=f"sqlite://{':memory:'}", modules={"models": ["tests.testmodels"]})
    assert "models" in Tortoise.apps
    assert connections.get("default") is not None


@pytest.mark.asyncio
async def test_init_wrong_connection_engine():
    await _reset_tortoise()
    with pytest.raises(ImportError, match="tortoise.backends.test"):
        await Tortoise.init(
            {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.test",
                        "credentials": {"file_path": ":memory:"},
                    }
                },
                "apps": {
                    "models": {"models": ["tests.testmodels"], "default_connection": "default"}
                },
            }
        )


@pytest.mark.asyncio
async def test_init_wrong_connection_engine_2():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError,
        match='Backend for engine "tortoise.backends" does not implement db client',
    ):
        await Tortoise.init(
            {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends",
                        "credentials": {"file_path": ":memory:"},
                    }
                },
                "apps": {
                    "models": {"models": ["tests.testmodels"], "default_connection": "default"}
                },
            }
        )


@pytest.mark.asyncio
async def test_init_no_connections():
    await _reset_tortoise()
    with pytest.raises(ConfigurationError, match='Config must define "connections" section'):
        await Tortoise.init(
            {"apps": {"models": {"models": ["tests.testmodels"], "default_connection": "default"}}}
        )


@pytest.mark.asyncio
async def test_init_no_apps():
    await _reset_tortoise()
    with pytest.raises(ConfigurationError, match='Config must define "apps" section'):
        await Tortoise.init(
            {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.sqlite",
                        "credentials": {"file_path": ":memory:"},
                    }
                }
            }
        )


@pytest.mark.asyncio
async def test_init_config_and_config_file():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError, match='You should init either from "config", "config_file" or "db_url"'
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
                    "models": {"models": ["tests.testmodels"], "default_connection": "default"}
                },
            },
            config_file="file.json",
        )


@pytest.mark.asyncio
async def test_init_config_file_wrong_extension():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError, match="Unknown config extension .ini, only .yml and .json are supported"
    ):
        await Tortoise.init(config_file="config.ini")


@pytest.mark.skipif(os.name == "nt", reason="path issue on Windows")
@pytest.mark.asyncio
async def test_init_json_file():
    await _reset_tortoise()
    await Tortoise.init(config_file=os.path.dirname(__file__) + "/init.json")
    assert "models" in Tortoise.apps
    assert connections.get("default") is not None


@pytest.mark.skipif(os.name == "nt", reason="path issue on Windows")
@pytest.mark.asyncio
async def test_init_yaml_file():
    await _reset_tortoise()
    await Tortoise.init(config_file=os.path.dirname(__file__) + "/init.yaml")
    assert "models" in Tortoise.apps
    assert connections.get("default") is not None


@pytest.mark.asyncio
async def test_generate_schema_without_init():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError, match=r"You have to call \.init\(\) first before generating schemas"
    ):
        await Tortoise.generate_schemas()


@pytest.mark.asyncio
async def test_drop_databases_without_init():
    await _reset_tortoise()
    with pytest.raises(
        ConfigurationError, match=r"You have to call \.init\(\) first before deleting schemas"
    ):
        await Tortoise._drop_databases()


@pytest.mark.asyncio
async def test_bad_models():
    await _reset_tortoise()
    with pytest.raises(ConfigurationError, match='Module "tests.testmodels2" not found'):
        await Tortoise.init(
            {
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.sqlite",
                        "credentials": {"file_path": ":memory:"},
                    }
                },
                "apps": {
                    "models": {"models": ["tests.testmodels2"], "default_connection": "default"}
                },
            }
        )
