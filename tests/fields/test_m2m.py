import pytest

from tests import testmodels
from tortoise.exceptions import OperationalError
from tortoise.fields import ManyToManyField


@pytest.mark.asyncio
async def test_empty(db):
    """Test creating M2M model without relations."""
    await testmodels.M2MOne.create()


@pytest.mark.asyncio
async def test__add(db):
    """Test adding a related object via M2M relation."""
    one = await testmodels.M2MOne.create(name="One")
    two = await testmodels.M2MTwo.create(name="Two")
    await one.two.add(two)
    assert await one.two == [two]
    assert await two.one == [one]


@pytest.mark.asyncio
async def test__add__nothing(db):
    """Test adding nothing to M2M relation."""
    one = await testmodels.M2MOne.create(name="One")
    await one.two.add()


@pytest.mark.asyncio
async def test__add__reverse(db):
    """Test adding via reverse M2M relation."""
    one = await testmodels.M2MOne.create(name="One")
    two = await testmodels.M2MTwo.create(name="Two")
    await two.one.add(one)
    assert await one.two == [two]
    assert await two.one == [one]


@pytest.mark.asyncio
async def test__add__many(db):
    """Test adding same object multiple times (should be idempotent)."""
    one = await testmodels.M2MOne.create(name="One")
    two = await testmodels.M2MTwo.create(name="Two")
    await one.two.add(two)
    await one.two.add(two)
    await two.one.add(one)
    assert await one.two == [two]
    assert await two.one == [one]


@pytest.mark.asyncio
async def test__add__two(db):
    """Test adding multiple related objects at once."""
    one = await testmodels.M2MOne.create(name="One")
    two1 = await testmodels.M2MTwo.create(name="Two")
    two2 = await testmodels.M2MTwo.create(name="Two")
    await one.two.add(two1, two2)
    assert await one.two == [two1, two2]
    assert await two1.one == [one]
    assert await two2.one == [one]


@pytest.mark.asyncio
async def test__remove(db):
    """Test removing one related object from M2M relation."""
    one = await testmodels.M2MOne.create(name="One")
    two1 = await testmodels.M2MTwo.create(name="Two")
    two2 = await testmodels.M2MTwo.create(name="Two")
    await one.two.add(two1, two2)
    await one.two.remove(two1)
    assert await one.two == [two2]
    assert await two1.one == []
    assert await two2.one == [one]


@pytest.mark.asyncio
async def test__remove__many(db):
    """Test removing multiple related objects at once."""
    one = await testmodels.M2MOne.create(name="One")
    two1 = await testmodels.M2MTwo.create(name="Two1")
    two2 = await testmodels.M2MTwo.create(name="Two2")
    two3 = await testmodels.M2MTwo.create(name="Two3")
    await one.two.add(two1, two2, two3)
    await one.two.remove(two1, two2)
    assert await one.two == [two3]
    assert await two1.one == []
    assert await two2.one == []
    assert await two3.one == [one]


@pytest.mark.asyncio
async def test__remove__blank(db):
    """Test that removing nothing raises OperationalError."""
    one = await testmodels.M2MOne.create(name="One")
    with pytest.raises(OperationalError, match=r"remove\(\) called on no instances"):
        await one.two.remove()


@pytest.mark.asyncio
async def test__clear(db):
    """Test clearing all related objects from M2M relation."""
    one = await testmodels.M2MOne.create(name="One")
    two1 = await testmodels.M2MTwo.create(name="Two")
    two2 = await testmodels.M2MTwo.create(name="Two")
    await one.two.add(two1, two2)
    await one.two.clear()
    assert await one.two == []
    assert await two1.one == []
    assert await two2.one == []


@pytest.mark.asyncio
async def test__uninstantiated_add(db):
    """Test that adding to unsaved model raises OperationalError."""
    one = testmodels.M2MOne(name="One")
    two = await testmodels.M2MTwo.create(name="Two")
    with pytest.raises(OperationalError, match=r"You should first call .save\(\) on <M2MOne>"):
        await one.two.add(two)


@pytest.mark.asyncio
async def test__add_uninstantiated(db):
    """Test that adding unsaved model raises OperationalError."""
    one = testmodels.M2MOne(name="One")
    two = await testmodels.M2MTwo.create(name="Two")
    with pytest.raises(OperationalError, match=r"You should first call .save\(\) on <M2MOne>"):
        await two.one.add(one)


@pytest.mark.asyncio
async def test_create_unique_index(db):
    """Test deprecated create_unique_index parameter behavior."""
    message = "Parameter `create_unique_index` is deprecated! Use `unique` instead."
    with pytest.warns(DeprecationWarning, match=message):
        field = ManyToManyField("models.Foo", create_unique_index=False)
    assert field.unique is False
    with pytest.warns(DeprecationWarning, match=message):
        field = ManyToManyField("models.Foo", create_unique_index=False, unique=True)
    assert field.unique is False
    with pytest.warns(DeprecationWarning, match=message):
        field = ManyToManyField("models.Foo", create_unique_index=True)
    assert field.unique is True
    with pytest.warns(DeprecationWarning, match=message):
        field = ManyToManyField("models.Foo", create_unique_index=True, unique=False)
    assert field.unique is True
    field = ManyToManyField(
        "models.Group",
    )
    assert field.unique is True
    field = ManyToManyField(
        "models.Group",
        "user_group",
        "user_id",
        "group_id",
        "users",
        "CASCADE",
        True,
        False,
    )
    assert field.unique is False
