import pytest

from tests.testmodels import Tournament
from tortoise import connections
from tortoise.contrib.test import requireCapability
from tortoise.transactions import in_transaction


@requireCapability(daemon=True)
@pytest.mark.asyncio
async def test_reconnect(db_isolated):
    """Test reconnection after connection expiry."""
    await Tournament.create(name="1")

    await connections.get("models")._expire_connections()

    await Tournament.create(name="2")

    await connections.get("models")._expire_connections()

    await Tournament.create(name="3")

    assert [f"{a.id}:{a.name}" for a in await Tournament.all()] == ["1:1", "2:2", "3:3"]


@requireCapability(daemon=True, supports_transactions=True)
@pytest.mark.asyncio
async def test_reconnect_transaction_start(db_isolated):
    """Test reconnection at transaction start."""
    async with in_transaction():
        await Tournament.create(name="1")

    await connections.get("models")._expire_connections()

    async with in_transaction():
        await Tournament.create(name="2")

    await connections.get("models")._expire_connections()

    async with in_transaction():
        assert [f"{a.id}:{a.name}" for a in await Tournament.all()] == ["1:1", "2:2"]
