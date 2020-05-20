import datetime
from decimal import Decimal

from tests.testmodels import DefaultModel
from tortoise.backends.asyncpg import AsyncpgDBClient
from tortoise.backends.mysql import MySQLClient
from tortoise.backends.sqlite import SqliteClient
from tortoise.contrib import test


class TestDefault(test.TestCase):
    async def setUp(self) -> None:
        connection = self.__db__
        if isinstance(connection, MySQLClient):
            await connection.execute_query(
                "insert into defaultmodel (`int_default`,`float_default`,`decimal_default`,`bool_default`,`char_default`,`date_default`,`datetime_default`) values (DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT)",
            )
        elif isinstance(connection, SqliteClient):
            await connection.execute_query("insert into defaultmodel default values",)
        elif isinstance(connection, AsyncpgDBClient):
            await connection.execute_query(
                'insert into defaultmodel ("int_default","float_default","decimal_default","bool_default","char_default","date_default","datetime_default") values (DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT)',
            )

    async def test_default(self):
        default_model = await DefaultModel.first()
        self.assertEqual(default_model.int_default, 1)
        self.assertEqual(default_model.float_default, 1.5)
        self.assertEqual(default_model.decimal_default, Decimal(1))
        self.assertTrue(default_model.bool_default)
        self.assertEqual(default_model.char_default, "tortoise")
        self.assertEqual(default_model.date_default, datetime.date.fromisoformat("2020-05-20"))
        self.assertEqual(
            default_model.datetime_default, datetime.datetime.fromisoformat("2020-05-20 00:00:00")
        )
