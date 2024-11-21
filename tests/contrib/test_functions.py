from tests.testmodels import IntFields
from tortoise import connections
from tortoise.contrib import test
from tortoise.contrib.mysql.functions import Rand
from tortoise.contrib.postgres.functions import Random as PostgresRandom
from tortoise.contrib.sqlite.functions import Random as SqliteRandom


class TestFunction(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.intfields = [await IntFields.create(intnum=val) for val in range(10)]
        self.db = connections.get("models")

    @test.requireCapability(dialect="mysql")
    async def test_mysql_func_rand(self):
        sql = IntFields.all().annotate(randnum=Rand()).values("intnum", "randnum").sql()
        expected_sql = "SELECT `intnum` `intnum`,RAND() `randnum` FROM `intfields`"
        self.assertEqual(sql, expected_sql)

    @test.requireCapability(dialect="mysql")
    async def test_mysql_func_rand_with_seed(self):
        sql = IntFields.all().annotate(randnum=Rand(0)).values("intnum", "randnum").sql()
        expected_sql = "SELECT `intnum` `intnum`,RAND(%s) `randnum` FROM `intfields`"
        self.assertEqual(sql, expected_sql)

    @test.requireCapability(dialect="postgres")
    async def test_postgres_func_rand(self):
        sql = IntFields.all().annotate(randnum=PostgresRandom()).values("intnum", "randnum").sql()
        expected_sql = 'SELECT "intnum" "intnum",RANDOM() "randnum" FROM "intfields"'
        self.assertEqual(sql, expected_sql)

    @test.requireCapability(dialect="sqlite")
    async def test_sqlite_func_rand(self):
        sql = IntFields.all().annotate(randnum=SqliteRandom()).values("intnum", "randnum").sql()
        expected_sql = 'SELECT "intnum" "intnum",RANDOM() "randnum" FROM "intfields"'
        self.assertEqual(sql, expected_sql)
