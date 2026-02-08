import uuid

import pytest

from tests import testmodels
from tortoise.exceptions import IntegrityError


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.UUIDFields.create()


@pytest.mark.asyncio
async def test_create(db):
    data = uuid.uuid4()
    obj0 = await testmodels.UUIDFields.create(data=data)
    assert isinstance(obj0.data, uuid.UUID)
    assert isinstance(obj0.data_auto, uuid.UUID)
    assert obj0.data_null is None
    obj = await testmodels.UUIDFields.get(id=obj0.id)
    assert isinstance(obj.data, uuid.UUID)
    assert isinstance(obj.data_auto, uuid.UUID)
    assert obj.data == data
    assert obj.data_null is None
    await obj.save()
    obj2 = await testmodels.UUIDFields.get(id=obj.id)
    assert obj == obj2

    await obj.delete()
    obj = await testmodels.UUIDFields.filter(id=obj0.id).first()
    assert obj is None


@pytest.mark.asyncio
async def test_update(db):
    data = uuid.uuid4()
    data2 = uuid.uuid4()
    obj0 = await testmodels.UUIDFields.create(data=data)
    await testmodels.UUIDFields.filter(id=obj0.id).update(data=data2)
    obj = await testmodels.UUIDFields.get(id=obj0.id)
    assert obj.data == data2
    assert obj.data_null is None


@pytest.mark.asyncio
async def test_create_not_null(db):
    data = uuid.uuid4()
    obj0 = await testmodels.UUIDFields.create(data=data, data_null=data)
    obj = await testmodels.UUIDFields.get(id=obj0.id)
    assert obj.data == data
    assert obj.data_null == data
