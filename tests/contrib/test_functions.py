import pytest
import pytest_asyncio

from tests.testmodels import IntFields, Tournament
from tortoise.contrib import test
from tortoise.contrib.mysql.functions import LPad as MySqlLPad
from tortoise.contrib.mysql.functions import Rand
from tortoise.contrib.mysql.functions import RPad as MySqlRPad
from tortoise.contrib.postgres.functions import (
    LPad as PostgresLPad,
)
from tortoise.contrib.postgres.functions import (
    Random as PostgresRandom,
)
from tortoise.contrib.postgres.functions import (
    RPad as PostgresRPad,
)
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


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_postgres_func_lpad(db):
    await Tournament.create(name="hello")
    await Tournament.create(name="my world")
    tournaments = await Tournament.annotate(pad_name=PostgresLPad("name", 12, "x"))
    result = set(tournament.pad_name for tournament in tournaments)
    assert result == {"xxxxmy world", "xxxxxxxhello"}


@test.requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_mysql_func_lpad(db):
    await Tournament.create(name="hello")
    await Tournament.create(name="my world")
    tournaments = await Tournament.annotate(pad_name=MySqlLPad("name", 12, "x"))
    result = set(tournament.pad_name for tournament in tournaments)
    assert result == {"xxxxmy world", "xxxxxxxhello"}


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_postgres_func_rpad(db):
    await Tournament.create(name="hello")
    await Tournament.create(name="my world")
    tournaments = await Tournament.annotate(pad_name=PostgresRPad("name", 12, "x"))
    result = set(tournament.pad_name for tournament in tournaments)
    assert result == {"my worldxxxx", "helloxxxxxxx"}


@test.requireCapability(dialect="mysql")
@pytest.mark.asyncio
async def test_mysql_func_rpad(db):
    await Tournament.create(name="hello")
    await Tournament.create(name="my world")
    tournaments = await Tournament.annotate(pad_name=MySqlRPad("name", 12, "x"))
    result = set(tournament.pad_name for tournament in tournaments)
    assert result == {"my worldxxxx", "helloxxxxxxx"}
