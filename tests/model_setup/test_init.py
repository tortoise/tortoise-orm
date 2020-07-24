import os

from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError


class TestInitErrors(test.SimpleTestCase):
    async def setUp(self):
        try:
            Tortoise.apps = {}
            Tortoise._connections = {}
            Tortoise._inited = False
        except ConfigurationError:
            pass
        Tortoise._inited = False

    async def tearDown(self):
        await Tortoise.close_connections()
        await Tortoise._reset_apps()

    async def test_basic_init(self):
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
            }
        )
        self.assertIn("models", Tortoise.apps)
        self.assertIsNotNone(Tortoise.get_connection("default"))

    async def test_empty_modules_init(self):
        with self.assertWarnsRegex(RuntimeWarning, 'Module "tests.model_setup" has no models'):
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

    async def test_dup1_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'backward relation "events" duplicates in model Tournament'
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

    async def test_dup2_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'backward relation "events" duplicates in model Team'
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

    async def test_dup3_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'backward relation "event" duplicates in model Tournament'
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

    async def test_generated_nonint(self):
        with self.assertRaisesRegex(
            ConfigurationError, "Field 'val' \\(CharField\\) can't be DB-generated"
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

    async def test_multiple_pk(self):
        with self.assertRaisesRegex(
            ConfigurationError,
            "Can't create model Tournament with two primary keys, only single primary key is supported",
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

    async def test_nonpk_id(self):
        with self.assertRaisesRegex(
            ConfigurationError,
            "Can't create model Tournament without explicit primary key if"
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

    async def test_unknown_connection(self):
        with self.assertRaisesRegex(ConfigurationError, 'Unknown connection "fioop"'):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {"file_path": ":memory:"},
                        }
                    },
                    "apps": {
                        "models": {"models": ["tests.testmodels"], "default_connection": "fioop"}
                    },
                }
            )

    async def test_url_without_modules(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'You must specify "db_url" and "modules" together'
        ):
            await Tortoise.init(db_url=f"sqlite://{':memory:'}")

    async def test_default_connection_init(self):
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
        self.assertIn("models", Tortoise.apps)
        self.assertIsNotNone(Tortoise.get_connection("default"))

    async def test_db_url_init(self):
        await Tortoise.init(
            {
                "connections": {"default": f"sqlite://{':memory:'}"},
                "apps": {
                    "models": {"models": ["tests.testmodels"], "default_connection": "default"}
                },
            }
        )
        self.assertIn("models", Tortoise.apps)
        self.assertIsNotNone(Tortoise.get_connection("default"))

    async def test_shorthand_init(self):
        await Tortoise.init(
            db_url=f"sqlite://{':memory:'}", modules={"models": ["tests.testmodels"]}
        )
        self.assertIn("models", Tortoise.apps)
        self.assertIsNotNone(Tortoise.get_connection("default"))

    async def test_init_wrong_connection_engine(self):
        with self.assertRaisesRegex(ImportError, "tortoise.backends.test"):
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

    async def test_init_wrong_connection_engine_2(self):
        with self.assertRaisesRegex(
            ConfigurationError,
            'Backend for engine "tortoise.backends" does not implement db client',
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

    async def test_init_no_connections(self):
        with self.assertRaisesRegex(ConfigurationError, 'Config must define "connections" section'):
            await Tortoise.init(
                {
                    "apps": {
                        "models": {"models": ["tests.testmodels"], "default_connection": "default"}
                    }
                }
            )

    async def test_init_no_apps(self):
        with self.assertRaisesRegex(ConfigurationError, 'Config must define "apps" section'):
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

    async def test_init_config_and_config_file(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'You should init either from "config", "config_file" or "db_url"'
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

    async def test_init_config_file_wrong_extension(self):
        with self.assertRaisesRegex(
            ConfigurationError, "Unknown config extension .ini, only .yml and .json are supported"
        ):
            await Tortoise.init(config_file="config.ini")

    @test.skipIf(os.name == "nt", "path issue on Windows")
    async def test_init_json_file(self):
        await Tortoise.init(config_file=os.path.dirname(__file__) + "/init.json")
        self.assertIn("models", Tortoise.apps)
        self.assertIsNotNone(Tortoise.get_connection("default"))

    @test.skipIf(os.name == "nt", "path issue on Windows")
    async def test_init_yaml_file(self):
        await Tortoise.init(config_file=os.path.dirname(__file__) + "/init.yaml")
        self.assertIn("models", Tortoise.apps)
        self.assertIsNotNone(Tortoise.get_connection("default"))

    async def test_generate_schema_without_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, r"You have to call \.init\(\) first before generating schemas"
        ):
            await Tortoise.generate_schemas()

    async def test_drop_databases_without_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, r"You have to call \.init\(\) first before deleting schemas"
        ):
            await Tortoise._drop_databases()

    async def test_bad_models(self):
        with self.assertRaisesRegex(ConfigurationError, 'Module "tests.testmodels2" not found'):
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
