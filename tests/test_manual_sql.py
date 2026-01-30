import pytest

from tortoise import connections
from tortoise.contrib.test import requireCapability
from tortoise.transactions import in_transaction


@pytest.mark.asyncio
async def test_simple_insert(db_truncate):
    """Test simple INSERT via raw SQL."""
    conn = connections.get("models")
    await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")
    assert await conn.execute_query_dict("SELECT name FROM author") == [{"name": "Foo"}]


@pytest.mark.asyncio
async def test_in_transaction(db_truncate):
    """Test INSERT inside transaction context manager."""
    async with in_transaction() as conn:
        await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")

    conn = connections.get("models")
    assert await conn.execute_query_dict("SELECT name FROM author") == [{"name": "Foo"}]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_in_transaction_exception(db_truncate):
    """Test that transaction rolls back on exception."""
    try:
        async with in_transaction() as conn:
            await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")
            raise ValueError("oops")
    except ValueError:
        pass

    conn = connections.get("models")
    assert await conn.execute_query_dict("SELECT name FROM author") == []


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_in_transaction_rollback(db_truncate):
    """Test explicit rollback inside transaction."""
    async with in_transaction() as conn:
        await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")
        await conn.rollback()

    conn = connections.get("models")
    assert await conn.execute_query_dict("SELECT name FROM author") == []


@pytest.mark.asyncio
async def test_in_transaction_commit(db_truncate):
    """Test explicit commit inside transaction persists data even on exception."""
    try:
        async with in_transaction() as conn:
            await conn.execute_query("INSERT INTO author (name) VALUES ('Foo')")
            await conn.commit()
            raise ValueError("oops")
    except ValueError:
        pass

    conn = connections.get("models")
    assert await conn.execute_query_dict("SELECT name FROM author") == [{"name": "Foo"}]
