import pytest

from tests import testmodels
from tortoise.exceptions import IntegrityError


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.BooleanFields.create()


@pytest.mark.asyncio
async def test_create(db):
    obj0 = await testmodels.BooleanFields.create(boolean=True)
    obj = await testmodels.BooleanFields.get(id=obj0.id)
    assert obj.boolean is True
    assert obj.boolean_null is None
    await obj.save()
    obj2 = await testmodels.BooleanFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_update(db):
    obj0 = await testmodels.BooleanFields.create(boolean=False)
    await testmodels.BooleanFields.filter(id=obj0.id).update(boolean=False)
    obj = await testmodels.BooleanFields.get(id=obj0.id)
    assert obj.boolean is False
    assert obj.boolean_null is None


@pytest.mark.asyncio
async def test_values(db):
    obj0 = await testmodels.BooleanFields.create(boolean=True)
    values = await testmodels.BooleanFields.get(id=obj0.id).values("boolean")
    assert values["boolean"] is True


@pytest.mark.asyncio
async def test_values_list(db):
    obj0 = await testmodels.BooleanFields.create(boolean=True)
    values = await testmodels.BooleanFields.get(id=obj0.id).values_list("boolean", flat=True)
    assert values is True
