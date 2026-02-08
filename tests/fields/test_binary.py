import pytest

from tests import testmodels
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.fields import BinaryField


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.BinaryFields.create()


@pytest.mark.asyncio
async def test_create(db):
    obj0 = await testmodels.BinaryFields.create(binary=bytes(range(256)) * 500)
    obj = await testmodels.BinaryFields.get(id=obj0.id)
    assert obj.binary == bytes(range(256)) * 500
    assert obj.binary_null is None
    await obj.save()
    obj2 = await testmodels.BinaryFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_values(db):
    obj0 = await testmodels.BinaryFields.create(
        binary=bytes(range(256)), binary_null=bytes(range(255, -1, -1))
    )
    values = await testmodels.BinaryFields.get(id=obj0.id).values("binary", "binary_null")
    assert values["binary"] == bytes(range(256))
    assert values["binary_null"] == bytes(range(255, -1, -1))


@pytest.mark.asyncio
async def test_values_list(db):
    obj0 = await testmodels.BinaryFields.create(binary=bytes(range(256)))
    values = await testmodels.BinaryFields.get(id=obj0.id).values_list("binary", flat=True)
    assert values == bytes(range(256))


def test_unique_fail():
    with pytest.raises(ConfigurationError, match="can't be indexed"):
        BinaryField(unique=True)


def test_index_fail():
    with pytest.warns(
        DeprecationWarning, match="`index` is deprecated, please use `db_index` instead"
    ):
        with pytest.raises(ConfigurationError, match="can't be indexed"):
            BinaryField(index=True)
    with pytest.raises(ConfigurationError, match="can't be indexed"):
        BinaryField(db_index=True)
