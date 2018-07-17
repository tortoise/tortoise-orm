from tortoise.backends.base.config_generator import generate_config
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError


class TestConfigGenerate(test.SimpleTestCase):

    def test_unknown_scheme(self):
        with self.assertRaises(ConfigurationError):
            generate_config(
                db_url='moo://baa',
                model_modules=['tortoise.tests.testmodels'],
                app_label='models',
            )

    def test_sqlite_basic(self):
        res = generate_config(
            db_url='sqlite:///tmp/test.sqlite',
            model_modules=['tortoise.tests.testmodels'],
            app_label='models',
        )
        self.assertDictEqual(res, {
            'connections': {
                'models': {
                    'engine': 'tortoise.backends.sqlite',
                    'credentials': {
                        'file_path': '/tmp/test.sqlite',
                    }
                },
            },
            'apps': {
                'models': {
                    'models': ['tortoise.tests.testmodels'],
                    'default_connection': 'models',
                }
            },
        })

    def test_sqlite_testing(self):
        res = generate_config(
            db_url='sqlite:///tmp/test-{}.sqlite',
            testing=True,
            model_modules=['tortoise.tests.testmodels'],
            app_label='models',
        )
        file_path = res['connections']['models']['credentials']['file_path']
        self.assertIn('/tmp/test-', file_path)  # nosec
        self.assertIn('.sqlite', file_path)
        self.assertNotEqual('sqlite:///tmp/test-{}.sqlite', file_path)
        self.assertDictEqual(res, {
            'connections': {
                'models': {
                    'engine': 'tortoise.backends.sqlite',
                    'credentials': {
                        'file_path': file_path,
                        'single_connection': True,
                    }
                },
            },
            'apps': {
                'models': {
                    'models': ['tortoise.tests.testmodels'],
                    'default_connection': 'models',
                }
            },
        })

    def test_sqlite_params(self):
        res = generate_config(
            db_url='sqlite:///tmp/test.sqlite?AHA=5&moo=yes',
            model_modules=['tortoise.tests.testmodels'],
            app_label='models',
        )
        self.assertDictEqual(res, {
            'connections': {
                'models': {
                    'engine': 'tortoise.backends.sqlite',
                    'credentials': {
                        'file_path': '/tmp/test.sqlite',
                        'AHA': '5',
                        'moo': 'yes',
                    }
                },
            },
            'apps': {
                'models': {
                    'models': ['tortoise.tests.testmodels'],
                    'default_connection': 'models',
                }
            },
        })

    def test_sqlite_invalid(self):
        with self.assertRaises(ConfigurationError):
            generate_config(
                db_url='sqlite://',
                model_modules=['tortoise.tests.testmodels'],
                app_label='models',
            )

    def test_postgres_basic(self):
        res = generate_config(
            db_url='postgres://postgres:@127.0.0.1:5432/test',
            model_modules=['tortoise.tests.testmodels'],
            app_label='models',
        )
        self.assertDictEqual(res, {
            'connections': {
                'models': {
                    'engine': 'tortoise.backends.asyncpg',
                    'credentials': {
                        'database': 'test',
                        'host': '127.0.0.1',
                        'password': '',
                        'port': '5432',
                        'user': 'postgres',
                    }
                },
            },
            'apps': {
                'models': {
                    'models': ['tortoise.tests.testmodels'],
                    'default_connection': 'models',
                }
            },
        })

    def test_postgres_nonint_port(self):
        with self.assertRaises(ConfigurationError):
            generate_config(
                db_url='postgres://postgres:@127.0.0.1:moo/test',
                model_modules=['tortoise.tests.testmodels'],
                app_label='models',
            )

    def test_postgres_testing(self):
        res = generate_config(
            db_url='postgres://postgres:@127.0.0.1:5432/test_\{\}',
            testing=True,
            model_modules=['tortoise.tests.testmodels'],
            app_label='models',
        )
        database = res['connections']['models']['credentials']['database']
        self.assertIn('test_', database)
        self.assertNotEqual('test_{}', database)
        self.assertDictEqual(res, {
            'connections': {
                'models': {
                    'engine': 'tortoise.backends.asyncpg',
                    'credentials': {
                        'database': database,
                        'host': '127.0.0.1',
                        'password': '',
                        'port': '5432',
                        'user': 'postgres',
                        'single_connection': True,
                    }
                },
            },
            'apps': {
                'models': {
                    'models': ['tortoise.tests.testmodels'],
                    'default_connection': 'models',
                }
            },
        })

    def test_postgres_params(self):
        res = generate_config(
            db_url='postgres://postgres:@127.0.0.1:5432/test?AHA=5&moo=yes',
            model_modules=['tortoise.tests.testmodels'],
            app_label='models',
        )
        self.assertDictEqual(res, {
            'connections': {
                'models': {
                    'engine': 'tortoise.backends.asyncpg',
                    'credentials': {
                        'database': 'test',
                        'host': '127.0.0.1',
                        'password': '',
                        'port': '5432',
                        'user': 'postgres',
                        'AHA': '5',
                        'moo': 'yes',
                    }
                },
            },
            'apps': {
                'models': {
                    'models': ['tortoise.tests.testmodels'],
                    'default_connection': 'models',
                }
            },
        })
