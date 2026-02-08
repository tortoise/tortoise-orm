import pytest
import pytest_asyncio

from tests.testmodels import IntFields
from tortoise.contrib import test
from tortoise.contrib.mysql.functions import Rand
from tortoise.contrib.postgres.functions import Random as PostgresRandom
from tortoise.contrib.sqlite.functions import Random as SqliteRandom


@pytest_asyncio.fixture
async def intfields(db):
    return [await IntFields.create(intnum=val) for val in range(10)]


@pytest.mark.asyncio
@test.requireCapability(dialect="mysql")
async def test_mysql_func_rand(db, intfields):
    sql = IntFields.all().annotate(randnum=Rand()).values("intnum", "randnum").sql()
    expected_sql = "SELECT `intnum` `intnum`,RAND() `randnum` FROM `intfields`"
    assert sql == expected_sql


@pytest.mark.asyncio
@test.requireCapability(dialect="mysql")
async def test_mysql_func_rand_with_seed(db, intfields):
    sql = IntFields.all().annotate(randnum=Rand(0)).values("intnum", "randnum").sql()
    expected_sql = "SELECT `intnum` `intnum`,RAND(%s) `randnum` FROM `intfields`"
    assert sql == expected_sql


@pytest.mark.asyncio
@test.requireCapability(dialect="postgres")
async def test_postgres_func_rand(db, intfields):
    sql = IntFields.all().annotate(randnum=PostgresRandom()).values("intnum", "randnum").sql()
    expected_sql = 'SELECT "intnum" "intnum",RANDOM() "randnum" FROM "intfields"'
    assert sql == expected_sql


@pytest.mark.asyncio
@test.requireCapability(dialect="sqlite")
async def test_sqlite_func_rand(db, intfields):
    sql = IntFields.all().annotate(randnum=SqliteRandom()).values("intnum", "randnum").sql()
    expected_sql = 'SELECT "intnum" "intnum",RANDOM() "randnum" FROM "intfields"'
    assert sql == expected_sql
