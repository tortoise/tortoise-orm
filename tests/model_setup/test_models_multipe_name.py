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

    async def test_init_duplicate_model_name(self):
        with self.assertRaisesRegex(
            ConfigurationError, "The model of the Author cannot be created twice."
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
                            "models": ["tests.testmodels", "tests.model_setup.models_multipe1"],
                            "default_connection": "default",
                        }
                    },
                }
            )

    async def test_init_duplicate_model_name2(self):
        with self.assertRaisesRegex(
            ConfigurationError, "The model of the Author cannot be created twice."
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
                            "models": ["tests.testmodels"],
                            "default_connection": "default",
                        },
                        "model3": {
                            "models": ["tests.model_setup.models_multipe3"],
                            "default_connection": "default",
                        },
                        "model2": {
                            "models": ["tests.model_setup.models_multipe2"],
                            "default_connection": "default",
                        },
                    },
                }
            )
