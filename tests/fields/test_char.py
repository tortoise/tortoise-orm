import pytest

from tests import testmodels
from tortoise import fields
from tortoise.exceptions import ConfigurationError, ValidationError


def test_max_length_missing():
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'max_length'"):
        fields.CharField()  # pylint: disable=E1120


def test_max_length_bad():
    with pytest.raises(ConfigurationError, match="'max_length' must be >= 1"):
        fields.CharField(max_length=0)


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(ValidationError):
        await testmodels.CharFields.create()


@pytest.mark.asyncio
async def test_create(db):
    obj0 = await testmodels.CharFields.create(char="moo")
    obj = await testmodels.CharFields.get(id=obj0.id)
    assert obj.char == "moo"
    assert obj.char_null is None
    await obj.save()
    obj2 = await testmodels.CharFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_update(db):
    obj0 = await testmodels.CharFields.create(char="moo")
    await testmodels.CharFields.filter(id=obj0.id).update(char="ba'a")
    obj = await testmodels.CharFields.get(id=obj0.id)
    assert obj.char == "ba'a"
    assert obj.char_null is None


@pytest.mark.asyncio
async def test_cast(db):
    obj0 = await testmodels.CharFields.create(char=33)
    obj = await testmodels.CharFields.get(id=obj0.id)
    assert obj.char == "33"


@pytest.mark.asyncio
async def test_values(db):
    obj0 = await testmodels.CharFields.create(char="moo")
    values = await testmodels.CharFields.get(id=obj0.id).values("char")
    assert values["char"] == "moo"


@pytest.mark.asyncio
async def test_values_list(db):
    obj0 = await testmodels.CharFields.create(char="moo")
    values = await testmodels.CharFields.get(id=obj0.id).values_list("char", flat=True)
    assert values == "moo"
