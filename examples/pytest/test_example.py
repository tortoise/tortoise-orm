import pytest

from examples.pytest.models import User


@pytest.mark.asyncio
async def test_create_user(db):
    user = await User.create(name="Alice")
    assert user.id is not None
    assert user.name == "Alice"


@pytest.mark.asyncio
async def test_query_user(db):
    await User.create(name="Bob")
    users = await User.filter(name="Bob")
    assert len(users) == 1


@pytest.mark.asyncio
async def test_isolation(db):
    count = await User.all().count()
    assert count == 0, "Database should be empty at test start"
