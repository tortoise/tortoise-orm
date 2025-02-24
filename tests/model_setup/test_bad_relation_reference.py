from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError


class TestBadRelationReferenceErrors(test.SimpleTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        try:
            Tortoise.apps = {}
            Tortoise._inited = False
        except ConfigurationError:
            pass
        Tortoise._inited = False

    async def asyncTearDown(self) -> None:
        await Tortoise._reset_apps()
        await super().asyncTearDown()

    async def test_wrong_app_init(self):
        with self.assertRaisesRegex(ConfigurationError, "No app with name 'app' registered."):
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

    async def test_wrong_model_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, "No model with name 'Tour' registered in app 'models'."
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

    async def test_no_app_in_reference_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'ForeignKeyField accepts model name in format "app.Model"'
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

    async def test_more_than_two_dots_in_reference_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'ForeignKeyField accepts model name in format "app.Model"'
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

    async def test_no_app_in_o2o_reference_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'OneToOneField accepts model name in format "app.Model"'
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

    async def test_non_unique_field_in_fk_reference_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'field "uuid" in model "Tournament" is not unique'
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

    async def test_non_exist_field_in_fk_reference_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'there is no field named "uuids" in model "Tournament"'
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

    async def test_non_unique_field_in_o2o_reference_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'field "uuid" in model "Tournament" is not unique'
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

    async def test_non_exist_field_in_o2o_reference_init(self):
        with self.assertRaisesRegex(
            ConfigurationError, 'there is no field named "uuids" in model "Tournament"'
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
