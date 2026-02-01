import datetime
from decimal import Decimal

import pytz

from tests.testmodels import DefaultModel
from tortoise import connections
from tortoise.backends.asyncpg import AsyncpgDBClient
from tortoise.backends.mssql import MSSQLClient
from tortoise.backends.mysql import MySQLClient
from tortoise.backends.oracle import OracleClient
from tortoise.backends.psycopg import PsycopgClient
from tortoise.backends.sqlite import SqliteClient
from tortoise.contrib import test


class TestDefault(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        db = connections.get("models")
        if isinstance(db, MySQLClient):
            await db.execute_query(
                "insert into defaultmodel (`int_default`,`float_default`,`decimal_default`,`bool_default`,`char_default`,`date_default`,`datetime_default`) values (DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT)",
            )
        elif isinstance(db, SqliteClient):
            await db.execute_query(
                "insert into defaultmodel default values",
            )
        elif isinstance(db, (AsyncpgDBClient, PsycopgClient, MSSQLClient)):
            await db.execute_query(
                'insert into defaultmodel ("int_default","float_default","decimal_default","bool_default","char_default","date_default","datetime_default") values (DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT)',
            )
        elif isinstance(db, OracleClient):
            await db.execute_query(
                'insert into "defaultmodel" ("int_default","float_default","decimal_default","bool_default","char_default","date_default","datetime_default") values (DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT)',
            )

    async def test_default(self):
        default_model = await DefaultModel.first()
        self.assertEqual(default_model.int_default, 1)
        self.assertEqual(default_model.float_default, 1.5)
        self.assertEqual(default_model.decimal_default, Decimal(1))
        self.assertTrue(default_model.bool_default)
        self.assertEqual(default_model.char_default, "tortoise")
        self.assertEqual(default_model.date_default, datetime.date(year=2020, month=5, day=21))
        self.assertEqual(
            default_model.datetime_default,
            datetime.datetime(year=2020, month=5, day=20, tzinfo=pytz.utc),
        )
