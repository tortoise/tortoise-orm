import uuid

import pytest

from tests import testmodels_mysql
from tortoise.exceptions import IntegrityError


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels_mysql.UUIDFields.create()


@pytest.mark.asyncio
async def test_create(db):
    data = uuid.uuid4()
    obj0 = await testmodels_mysql.UUIDFields.create(data=data)
    assert isinstance(obj0.data, bytes)
    assert isinstance(obj0.data_auto, bytes)
    assert obj0.data_null is None
    obj = await testmodels_mysql.UUIDFields.get(id=obj0.id)
    assert isinstance(obj.data, uuid.UUID)
    assert isinstance(obj.data_auto, uuid.UUID)
    assert obj.data == data
    assert obj.data_null is None
    await obj.save()
    obj2 = await testmodels_mysql.UUIDFields.get(id=obj.id)
    assert obj == obj2

    await obj.delete()
    obj = await testmodels_mysql.UUIDFields.filter(id=obj0.id).first()
    assert obj is None


@pytest.mark.asyncio
async def test_update(db):
    data = uuid.uuid4()
    data2 = uuid.uuid4()
    obj0 = await testmodels_mysql.UUIDFields.create(data=data)
    await testmodels_mysql.UUIDFields.filter(id=obj0.id).update(data=data2)
    obj = await testmodels_mysql.UUIDFields.get(id=obj0.id)
    assert obj.data == data2
    assert obj.data_null is None


@pytest.mark.asyncio
async def test_create_not_null(db):
    data = uuid.uuid4()
    obj0 = await testmodels_mysql.UUIDFields.create(data=data, data_null=data)
    obj = await testmodels_mysql.UUIDFields.get(id=obj0.id)
    assert obj.data == data
    assert obj.data_null == data
