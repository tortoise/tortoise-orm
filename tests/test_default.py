import datetime
from decimal import Decimal

import pytest
import pytest_asyncio

from tests.testmodels import DefaultModel
from tortoise import connections
from tortoise.backends.asyncpg import AsyncpgDBClient
from tortoise.backends.mysql import MySQLClient
from tortoise.backends.psycopg import PsycopgClient
from tortoise.backends.sqlite import SqliteClient
from tortoise.timezone import UTC

# Optional imports for database clients that require system dependencies
try:
    from tortoise.backends.mssql import MSSQLClient
except ImportError:
    MSSQLClient = None  # type: ignore[misc,assignment]

try:
    from tortoise.backends.oracle import OracleClient
except ImportError:
    OracleClient = None  # type: ignore[misc,assignment]


@pytest_asyncio.fixture
async def default_row(db):
    """Insert a default row using raw SQL based on database type."""
    db_conn = connections.get("models")
    if isinstance(db_conn, MySQLClient):
        await db_conn.execute_query(
            "insert into defaultmodel (`int_default`,`float_default`,`decimal_default`,`bool_default`,`char_default`,`date_default`,`datetime_default`) values (DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT)",
        )
    elif isinstance(db_conn, SqliteClient):
        await db_conn.execute_query(
            "insert into defaultmodel default values",
        )
    elif isinstance(db_conn, (AsyncpgDBClient, PsycopgClient)) or (
        MSSQLClient is not None and isinstance(db_conn, MSSQLClient)
    ):
        await db_conn.execute_query(
            'insert into defaultmodel ("int_default","float_default","decimal_default","bool_default","char_default","date_default","datetime_default") values (DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT)',
        )
    elif OracleClient is not None and isinstance(db_conn, OracleClient):
        await db_conn.execute_query(
            'insert into "defaultmodel" ("int_default","float_default","decimal_default","bool_default","char_default","date_default","datetime_default") values (DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT,DEFAULT)',
        )
    yield


@pytest.mark.asyncio
async def test_default(default_row):
    """Test that default values are correctly applied when inserting via raw SQL."""
    default_model = await DefaultModel.first()
    assert default_model.int_default == 1
    assert default_model.float_default == 1.5
    assert default_model.decimal_default == Decimal(1)
    assert default_model.bool_default
    assert default_model.char_default == "tortoise"
    assert default_model.date_default == datetime.date(year=2020, month=5, day=21)
    assert default_model.datetime_default == datetime.datetime(
        year=2020, month=5, day=20, tzinfo=UTC
    )
