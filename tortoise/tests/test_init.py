import os
import tempfile
import uuid

from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError


class TestInitErrors(test.SimpleTestCase):
    async def test_basic_init(self):
        db_file_path = os.path.join(
            tempfile.gettempdir(),
            "test_{}.sqlite3".format(uuid.uuid4().hex)
        )
        await Tortoise.init({
            "connections": {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {
                        "file_path": db_file_path,
                    }
                }
            },
            "apps": {
                "models": {
                    "models": [
                        "tortoise.tests.testmodels",
                    ],
                    "default_connection": "default"
                }
            }
        })
        self.assertTrue('models' in Tortoise.apps)
        self.assertIsNotNone(Tortoise.get_connection('default'))

    async def test_init_wrong_connection_engine(self):
        db_file_path = os.path.join(
            tempfile.gettempdir(),
            "test_{}.sqlite3".format(uuid.uuid4().hex)
        )
        with self.assertRaisesRegex(
                ConfigurationError,
                'Backend for engine "tortoise.backends.test" not found',
        ):
            await Tortoise.init({
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.test",
                        "credentials": {
                            "file_path": db_file_path
                        }
                    }
                },
                "apps": {
                    "models": {
                        "models": ["tortoise.tests.testmodels"],
                        "default_connection": "default"
                    }
                }
            })

    async def test_init_no_connections(self):
        with self.assertRaisesRegex(
                ConfigurationError,
                'Config must define "connections" section',
        ):
            await Tortoise.init({
                "apps": {
                    "models": {
                        "models": ["tortoise.tests.testmodels"],
                        "default_connection": "default"
                    }
                }
            })

    async def test_init_no_apps(self):
        db_file_path = os.path.join(
            tempfile.gettempdir(),
            "test_{}.sqlite3".format(uuid.uuid4().hex)
        )
        with self.assertRaisesRegex(
                ConfigurationError,
                'Config must define "apps" section',
        ):
            await Tortoise.init({
                "connections": {
                    "default": {
                        "engine": "tortoise.backends.sqlite",
                        "credentials": {
                            "file_path": db_file_path,
                        }
                    }
                },
            })

    async def test_init_config_and_config_file(self):
        db_file_path = os.path.join(
            tempfile.gettempdir(),
            "test_{}.sqlite3".format(uuid.uuid4().hex)
        )
        with self.assertRaisesRegex(
                ConfigurationError,
                'You should init either from "config" or "config_file"',
        ):
            await Tortoise.init(
                {
                    "connections": {
                        "default": {
                            "engine": "tortoise.backends.sqlite",
                            "credentials": {
                                "file_path": db_file_path
                            }
                        }
                    },
                    "apps": {
                        "models": {
                            "models": ["tortoise.tests.testmodels"],
                            "default_connection": "default"
                        }
                    }
                },
                config_file='file.json',
            )

    async def test_init_config_file_wrong_extension(self):
        with self.assertRaisesRegex(
                ConfigurationError,
                'Unknown config extension .ini, only .yml and .json are supported',
        ):
            await Tortoise.init(config_file='config.ini')
