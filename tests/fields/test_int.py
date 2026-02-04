import pytest

from tests import testmodels
from tortoise.exceptions import IntegrityError
from tortoise.expressions import F

# ============================================================================
# TestIntFields
# ============================================================================


@pytest.mark.asyncio
async def test_int_fields_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.IntFields.create()


@pytest.mark.asyncio
async def test_int_fields_create(db):
    obj0 = await testmodels.IntFields.create(intnum=2147483647)
    obj = await testmodels.IntFields.get(id=obj0.id)
    assert obj.intnum == 2147483647
    assert obj.intnum_null is None

    obj2 = await testmodels.IntFields.get(id=obj.id)
    assert obj == obj2

    await obj.delete()
    obj = await testmodels.IntFields.filter(id=obj0.id).first()
    assert obj is None


@pytest.mark.asyncio
async def test_int_fields_update(db):
    obj0 = await testmodels.IntFields.create(intnum=2147483647)
    await testmodels.IntFields.filter(id=obj0.id).update(intnum=2147483646)
    obj = await testmodels.IntFields.get(id=obj0.id)
    assert obj.intnum == 2147483646
    assert obj.intnum_null is None


@pytest.mark.asyncio
async def test_int_fields_min(db):
    obj0 = await testmodels.IntFields.create(intnum=-2147483648)
    obj = await testmodels.IntFields.get(id=obj0.id)
    assert obj.intnum == -2147483648
    assert obj.intnum_null is None

    obj2 = await testmodels.IntFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_int_fields_cast(db):
    obj0 = await testmodels.IntFields.create(intnum="3")
    obj = await testmodels.IntFields.get(id=obj0.id)
    assert obj.intnum == 3


@pytest.mark.asyncio
async def test_int_fields_values(db):
    obj0 = await testmodels.IntFields.create(intnum=1)
    values = await testmodels.IntFields.get(id=obj0.id).values("intnum")
    assert values["intnum"] == 1


@pytest.mark.asyncio
async def test_int_fields_values_list(db):
    obj0 = await testmodels.IntFields.create(intnum=1)
    values = await testmodels.IntFields.get(id=obj0.id).values_list("intnum", flat=True)
    assert values == 1


@pytest.mark.asyncio
async def test_int_fields_f_expression(db):
    obj0 = await testmodels.IntFields.create(intnum=1)
    await obj0.filter(id=obj0.id).update(intnum=F("intnum") + 1)
    obj1 = await testmodels.IntFields.get(id=obj0.id)
    assert obj1.intnum == 2


# ============================================================================
# TestSmallIntFields
# ============================================================================


@pytest.mark.asyncio
async def test_small_int_fields_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.SmallIntFields.create()


@pytest.mark.asyncio
async def test_small_int_fields_create(db):
    obj0 = await testmodels.SmallIntFields.create(smallintnum=32767)
    obj = await testmodels.SmallIntFields.get(id=obj0.id)
    assert obj.smallintnum == 32767
    assert obj.smallintnum_null is None
    await obj.save()
    obj2 = await testmodels.SmallIntFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_small_int_fields_min(db):
    obj0 = await testmodels.SmallIntFields.create(smallintnum=-32768)
    obj = await testmodels.SmallIntFields.get(id=obj0.id)
    assert obj.smallintnum == -32768
    assert obj.smallintnum_null is None
    await obj.save()
    obj2 = await testmodels.SmallIntFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_small_int_fields_values(db):
    obj0 = await testmodels.SmallIntFields.create(smallintnum=2)
    values = await testmodels.SmallIntFields.get(id=obj0.id).values("smallintnum")
    assert values["smallintnum"] == 2


@pytest.mark.asyncio
async def test_small_int_fields_values_list(db):
    obj0 = await testmodels.SmallIntFields.create(smallintnum=2)
    values = await testmodels.SmallIntFields.get(id=obj0.id).values_list("smallintnum", flat=True)
    assert values == 2


@pytest.mark.asyncio
async def test_small_int_fields_f_expression(db):
    obj0 = await testmodels.SmallIntFields.create(smallintnum=1)
    await obj0.filter(id=obj0.id).update(smallintnum=F("smallintnum") + 1)
    obj1 = await testmodels.SmallIntFields.get(id=obj0.id)
    assert obj1.smallintnum == 2


# ============================================================================
# TestBigIntFields
# ============================================================================


@pytest.mark.asyncio
async def test_big_int_fields_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.BigIntFields.create()


@pytest.mark.asyncio
async def test_big_int_fields_create(db):
    obj0 = await testmodels.BigIntFields.create(intnum=9223372036854775807)
    obj = await testmodels.BigIntFields.get(id=obj0.id)
    assert obj.intnum == 9223372036854775807
    assert obj.intnum_null is None
    await obj.save()
    obj2 = await testmodels.BigIntFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_big_int_fields_min(db):
    obj0 = await testmodels.BigIntFields.create(intnum=-9223372036854775808)
    obj = await testmodels.BigIntFields.get(id=obj0.id)
    assert obj.intnum == -9223372036854775808
    assert obj.intnum_null is None
    await obj.save()
    obj2 = await testmodels.BigIntFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_big_int_fields_cast(db):
    obj0 = await testmodels.BigIntFields.create(intnum="3")
    obj = await testmodels.BigIntFields.get(id=obj0.id)
    assert obj.intnum == 3


@pytest.mark.asyncio
async def test_big_int_fields_values(db):
    obj0 = await testmodels.BigIntFields.create(intnum=1)
    values = await testmodels.BigIntFields.get(id=obj0.id).values("intnum")
    assert values["intnum"] == 1


@pytest.mark.asyncio
async def test_big_int_fields_values_list(db):
    obj0 = await testmodels.BigIntFields.create(intnum=1)
    values = await testmodels.BigIntFields.get(id=obj0.id).values_list("intnum", flat=True)
    assert values == 1


@pytest.mark.asyncio
async def test_big_int_fields_f_expression(db):
    obj0 = await testmodels.BigIntFields.create(intnum=1)
    await obj0.filter(id=obj0.id).update(intnum=F("intnum") + 1)
    obj1 = await testmodels.BigIntFields.get(id=obj0.id)
    assert obj1.intnum == 2
