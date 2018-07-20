from tortoise.backends.asyncpg.client import AsyncpgDBClient
from tortoise.backends.base.db_url import expand_db_url
from tortoise.backends.mysql.client import MySQLClient
from tortoise.backends.sqlite.client import SqliteClient
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError


class TestDBUrl(test.SimpleTestCase):

    def test_unknown_scheme(self):
        with self.assertRaises(ConfigurationError):
            expand_db_url('moo://baa')

    def test_sqlite_basic(self):
        res = expand_db_url('sqlite:///tmp/test.sqlite')
        self.assertEqual(res, {
            'client': SqliteClient,
            'params': {
                'filename': '/tmp/test.sqlite',  # nosec
            }
        })

    def test_sqlite_testing(self):
        res = expand_db_url('sqlite:///tmp/test-{}.sqlite', testing=True)
        self.assertIn('/tmp/test-', res['params']['filename'])  # nosec
        self.assertIn('.sqlite', res['params']['filename'])
        self.assertNotEqual('sqlite:///tmp/test-{}.sqlite', res['params']['filename'])
        self.assertEqual(res, {
            'client': SqliteClient,
            'params': {
                'filename': res['params']['filename'],
                'single_connection': True,
            }
        })

    def test_sqlite_params(self):
        res = expand_db_url('sqlite:///tmp/test.sqlite?AHA=5&moo=yes')
        self.assertEqual(res, {
            'client': SqliteClient,
            'params': {
                'filename': '/tmp/test.sqlite',  # nosec
                'AHA': '5',
                'moo': 'yes',
            }
        })

    def test_sqlite_invalid(self):
        with self.assertRaises(ConfigurationError):
            expand_db_url('sqlite://')

    def test_postgres_basic(self):
        res = expand_db_url('postgres://postgres:@127.0.0.1:5432/test')
        self.assertEqual(res, {
            'client': AsyncpgDBClient,
            'params': {
                'database': 'test',
                'host': '127.0.0.1',
                'password': '',
                'port': '5432',
                'user': 'postgres',
            }
        })

    def test_postgres_nonint_port(self):
        with self.assertRaises(ConfigurationError):
            expand_db_url('postgres://postgres:@127.0.0.1:moo/test')

    def test_postgres_testing(self):
        res = expand_db_url('postgres://postgres:@127.0.0.1:5432/test_\{\}', testing=True)
        self.assertIn('test_', res['params']['database'])
        self.assertNotEqual('test_{}', res['params']['database'])
        self.assertEqual(res, {
            'client': AsyncpgDBClient,
            'params': {
                'database': res['params']['database'],
                'host': '127.0.0.1',
                'password': '',
                'port': '5432',
                'user': 'postgres',
                'single_connection': True,
            }
        })

    def test_postgres_params(self):
        res = expand_db_url('postgres://postgres:@127.0.0.1:5432/test?AHA=5&moo=yes')
        self.assertEqual(res, {
            'client': AsyncpgDBClient,
            'params': {
                'database': 'test',
                'host': '127.0.0.1',
                'password': '',
                'port': '5432',
                'user': 'postgres',
                'AHA': '5',
                'moo': 'yes',
            }
        })

    def test_mysql_basic(self):
        res = expand_db_url('mysql://mysql:@127.0.0.1:3306/test')
        self.assertEqual(res, {
            'client': MySQLClient,
            'params': {
                'database': 'test',
                'host': '127.0.0.1',
                'password': '',
                'port': '3306',
                'user': 'mysql',
            }
        })

    def test_mysql_nonint_port(self):
        with self.assertRaises(ConfigurationError):
            expand_db_url('mysql://mysql:@127.0.0.1:moo/test')

    def test_mysql_testing(self):
        res = expand_db_url('mysql://mysql:@127.0.0.1:3306/test_\{\}', testing=True)
        self.assertIn('test_', res['params']['database'])
        self.assertNotEqual('test_{}', res['params']['database'])
        self.assertEqual(res, {
            'client': MySQLClient,
            'params': {
                'database': res['params']['database'],
                'host': '127.0.0.1',
                'password': '',
                'port': '3306',
                'user': 'mysql',
                'single_connection': True,
            }
        })

    def test_mysql_params(self):
        res = expand_db_url('mysql://mysql:@127.0.0.1:3306/test?AHA=5&moo=yes')
        self.assertEqual(res, {
            'client': AsyncpgDBClient,
            'params': {
                'database': 'test',
                'host': '127.0.0.1',
                'password': '',
                'port': '3306',
                'user': 'postgres',
                'AHA': '5',
                'moo': 'yes',
            }
        })
