from decimal import Decimal

import pytest

from tests import testmodels
from tortoise.exceptions import IntegrityError
from tortoise.expressions import F


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.FloatFields.create()


@pytest.mark.asyncio
async def test_create(db):
    obj0 = await testmodels.FloatFields.create(floatnum=1.23)
    obj = await testmodels.FloatFields.get(id=obj0.id)
    assert obj.floatnum == 1.23
    assert Decimal(obj.floatnum) != Decimal("1.23")
    assert obj.floatnum_null is None
    await obj.save()
    obj2 = await testmodels.FloatFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_update(db):
    obj0 = await testmodels.FloatFields.create(floatnum=1.23)
    await testmodels.FloatFields.filter(id=obj0.id).update(floatnum=2.34)
    obj = await testmodels.FloatFields.get(id=obj0.id)
    assert obj.floatnum == 2.34
    assert Decimal(obj.floatnum) != Decimal("2.34")
    assert obj.floatnum_null is None


@pytest.mark.asyncio
async def test_cast_int(db):
    obj0 = await testmodels.FloatFields.create(floatnum=123)
    obj = await testmodels.FloatFields.get(id=obj0.id)
    assert obj.floatnum == 123


@pytest.mark.asyncio
async def test_cast_decimal(db):
    obj0 = await testmodels.FloatFields.create(floatnum=Decimal("1.23"))
    obj = await testmodels.FloatFields.get(id=obj0.id)
    assert obj.floatnum == 1.23


@pytest.mark.asyncio
async def test_values(db):
    obj0 = await testmodels.FloatFields.create(floatnum=1.23)
    values = await testmodels.FloatFields.filter(id=obj0.id).values("floatnum")
    assert values[0]["floatnum"] == 1.23


@pytest.mark.asyncio
async def test_values_list(db):
    obj0 = await testmodels.FloatFields.create(floatnum=1.23)
    values = await testmodels.FloatFields.filter(id=obj0.id).values_list("floatnum")
    assert list(values[0]) == [1.23]


@pytest.mark.asyncio
async def test_f_expression(db):
    obj0 = await testmodels.FloatFields.create(floatnum=1.23)
    await obj0.filter(id=obj0.id).update(floatnum=F("floatnum") + 0.01)
    obj1 = await testmodels.FloatFields.get(id=obj0.id)
    assert obj1.floatnum == 1.24
