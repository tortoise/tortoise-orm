import pytest

from tests import testmodels
from tortoise.exceptions import IntegrityError
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


def test_index_options_are_deferred_to_the_database_dialect():
    assert TextField(unique=True).unique is True
    assert TextField(db_index=True).index is True
    with pytest.warns(
        DeprecationWarning, match="`index` is deprecated, please use `db_index` instead"
    ):
        assert TextField(index=True).index is True


def test_pk_deprecated():
    with pytest.warns(
        DeprecationWarning, match="TextField as a PrimaryKey is Deprecated, use CharField"
    ):
        TextField(primary_key=True)
