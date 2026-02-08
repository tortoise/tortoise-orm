import pytest

from tests import testmodels
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.fields import TextField


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.TextFields.create()


@pytest.mark.asyncio
async def test_create(db):
    obj0 = await testmodels.TextFields.create(text="baaa" * 32000)
    obj = await testmodels.TextFields.get(id=obj0.id)
    assert obj.text == "baaa" * 32000
    assert obj.text_null is None
    await obj.save()
    obj2 = await testmodels.TextFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_values(db):
    obj0 = await testmodels.TextFields.create(text="baa")
    values = await testmodels.TextFields.get(id=obj0.id).values("text")
    assert values["text"] == "baa"


@pytest.mark.asyncio
async def test_values_list(db):
    obj0 = await testmodels.TextFields.create(text="baa")
    values = await testmodels.TextFields.get(id=obj0.id).values_list("text", flat=True)
    assert values == "baa"


def test_unique_fail():
    msg = "TextField can't be indexed, consider CharField"
    with pytest.raises(ConfigurationError, match=msg):
        with pytest.warns(
            DeprecationWarning, match="`index` is deprecated, please use `db_index` instead"
        ):
            TextField(index=True)
    with pytest.raises(ConfigurationError, match=msg):
        TextField(db_index=True)


def test_index_fail():
    with pytest.raises(ConfigurationError, match="can't be indexed, consider CharField"):
        TextField(index=True)


def test_pk_deprecated():
    with pytest.warns(
        DeprecationWarning, match="TextField as a PrimaryKey is Deprecated, use CharField"
    ):
        TextField(primary_key=True)
