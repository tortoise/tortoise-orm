from tortoise.backends.base.config_generator import expand_db_url, generate_config
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError


class TestConfigGenerator(test.SimpleTestCase):

    def test_unknown_scheme(self):
        with self.assertRaises(ConfigurationError):
            expand_db_url('moo://baa')

    def test_sqlite_basic(self):
        res = expand_db_url('sqlite:///some/test.sqlite')
        self.assertDictEqual(res, {
            'engine': 'tortoise.backends.sqlite',
            'credentials': {
                'file_path': '/some/test.sqlite',
            }
        })

    def test_sqlite_params(self):
        res = expand_db_url('sqlite:///some/test.sqlite?AHA=5&moo=yes')
        self.assertDictEqual(res, {
            'engine': 'tortoise.backends.sqlite',
            'credentials': {
                'file_path': '/some/test.sqlite',
                'AHA': '5',
                'moo': 'yes',
            }
        })

    def test_sqlite_invalid(self):
        with self.assertRaises(ConfigurationError):
            expand_db_url('sqlite://')

    def test_postgres_basic(self):
        res = expand_db_url('postgres://postgres:@some.host:5432/test')
        self.assertDictEqual(res, {
            'engine': 'tortoise.backends.asyncpg',
            'credentials': {
                'database': 'test',
                'host': 'some.host',
                'password': '',
                'port': '5432',
                'user': 'postgres',
            }
        })

    def test_postgres_nonint_port(self):
        with self.assertRaises(ConfigurationError):
            expand_db_url('postgres://postgres:@some.host:moo/test')

    def test_postgres_params(self):
        res = expand_db_url('postgres://postgres:@some.host:5432/test?AHA=5&moo=yes')
        self.assertDictEqual(res, {
            'engine': 'tortoise.backends.asyncpg',
            'credentials': {
                'database': 'test',
                'host': 'some.host',
                'password': '',
                'port': '5432',
                'user': 'postgres',
                'AHA': '5',
                'moo': 'yes',
            }
        })

    def test_mysql_basic(self):
        res = expand_db_url('mysql://root:@some.host:3306/test')
        self.assertEqual(res, {
            'engine': 'tortoise.backends.mysql',
            'credentials': {
                'database': 'test',
                'host': 'some.host',
                'password': '',
                'port': '3306',
                'user': 'root',
            }
        })

    def test_mysql_nonint_port(self):
        with self.assertRaises(ConfigurationError):
            expand_db_url('mysql://root:@some.host:moo/test')

    def test_mysql_params(self):
        res = expand_db_url('mysql://root:@some.host:3306/test?AHA=5&moo=yes')
        self.assertEqual(res, {
            'engine': 'tortoise.backends.mysql',
            'credentials': {
                'database': 'test',
                'host': 'some.host',
                'password': '',
                'port': '3306',
                'user': 'root',
                'AHA': '5',
                'moo': 'yes',
            }
        })

    def test_generate_config_basic(self):
        res = generate_config(
            db_url='sqlite:///some/test.sqlite',
            app_modules={
                'models': [
                    'one.models',
                    'two.models'
                ]
            }
        )
        self.assertEqual(res, {
            'connections': {
                'default': {
                    'credentials': {
                        'file_path': '/some/test.sqlite'
                    },
                    'engine': 'tortoise.backends.sqlite'
                }
            },
            'apps': {
                'models': {
                    'models': [
                        'one.models',
                        'two.models'
                    ],
                    'default_connection': 'default'
                }
            },
        })

    def test_generate_config_explicit(self):
        res = generate_config(
            db_url='sqlite:///some/test.sqlite',
            app_modules={
                'models': [
                    'one.models',
                    'two.models'
                ]
            },
            connection_label='models',
        )
        self.assertEqual(res, {
            'connections': {
                'models': {
                    'credentials': {
                        'file_path': '/some/test.sqlite',
                    },
                    'engine': 'tortoise.backends.sqlite'
                }
            },
            'apps': {
                'models': {
                    'models': [
                        'one.models',
                        'two.models'
                    ],
                    'default_connection': 'models'
                }
            },
        })

    def test_generate_config_many_apps(self):
        res = generate_config(
            db_url='sqlite:///some/test.sqlite',
            app_modules={
                'models': [
                    'one.models',
                    'two.models'
                ],
                'peanuts': [
                    'peanut.models'
                ]
            }
        )
        self.assertEqual(res, {
            'connections': {
                'default': {
                    'credentials': {
                        'file_path': '/some/test.sqlite'
                    },
                    'engine': 'tortoise.backends.sqlite'
                }
            },
            'apps': {
                'models': {
                    'models': [
                        'one.models',
                        'two.models'
                    ],
                    'default_connection': 'default'
                },
                'peanuts': {
                    'models': [
                        'peanut.models'
                    ],
                    'default_connection': 'default'
                }
            }
        })
