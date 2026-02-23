import pytest

from tests import testmodels
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import In
from tortoise.exceptions import (
    ConfigurationError,
    DoesNotExist,
    FieldError,
    IntegrityError,
)
from tortoise.fields import JSONField


@pytest.mark.asyncio
async def test_empty(db):
    """Test that creating without required JSON field raises IntegrityError."""
    with pytest.raises(IntegrityError):
        await testmodels.JSONFields.create()


@pytest.mark.asyncio
async def test_create(db):
    """Test JSON field creation and retrieval."""
    obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})
    obj = await testmodels.JSONFields.get(id=obj0.id)
    assert obj.data == {"some": ["text", 3]}
    assert obj.data_null is None
    await obj.save()
    obj2 = await testmodels.JSONFields.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_error(db):
    """Test that invalid JSON raises FieldError."""
    with pytest.raises(FieldError):
        await testmodels.JSONFields.create(data='{"some": ')

    obj = await testmodels.JSONFields.create(data='{"some": ["text", 3]}')
    with pytest.raises(FieldError):
        await testmodels.JSONFields.filter(pk=obj.pk).update(data='{"some": ')

    with pytest.raises(FieldError):
        obj.data = "error json"
        await obj.save()


@pytest.mark.asyncio
async def test_update(db):
    """Test JSON field update."""
    obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})
    await testmodels.JSONFields.filter(id=obj0.id).update(data={"other": ["text", 5]})
    obj = await testmodels.JSONFields.get(id=obj0.id)
    assert obj.data == {"other": ["text", 5]}
    assert obj.data_null is None


@pytest.mark.asyncio
async def test_dict_str(db):
    """Test JSON field with dict from string."""
    obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})

    obj = await testmodels.JSONFields.get(id=obj0.id)
    assert obj.data == {"some": ["text", 3]}

    await testmodels.JSONFields.filter(id=obj0.id).update(data='{"other": ["text", 5]}')
    obj = await testmodels.JSONFields.get(id=obj0.id)
    assert obj.data == {"other": ["text", 5]}


@pytest.mark.asyncio
async def test_list_str(db):
    """Test JSON field with list from string."""
    obj = await testmodels.JSONFields.create(data='["text", 3]')
    obj0 = await testmodels.JSONFields.get(id=obj.id)
    assert obj0.data == ["text", 3]

    await testmodels.JSONFields.filter(id=obj.id).update(data='["text", 5]')
    obj0 = await testmodels.JSONFields.get(id=obj.id)
    assert obj0.data == ["text", 5]


@pytest.mark.asyncio
async def test_list(db):
    """Test JSON field with list data."""
    obj0 = await testmodels.JSONFields.create(data=["text", 3])
    obj = await testmodels.JSONFields.get(id=obj0.id)
    assert obj.data == ["text", 3]
    assert obj.data_null is None
    await obj.save()
    obj2 = await testmodels.JSONFields.get(id=obj.id)
    assert obj == obj2


@requireCapability(dialect=In("mysql", "postgres"))
@pytest.mark.asyncio
async def test_list_contains(db):
    """Test JSON contains filter on list."""
    await testmodels.JSONFields.create(data=["text", 3, {"msg": "msg2"}])
    obj = await testmodels.JSONFields.filter(data__contains=[{"msg": "msg2"}]).first()
    assert obj.data == ["text", 3, {"msg": "msg2"}]
    await obj.save()
    obj2 = await testmodels.JSONFields.get(id=obj.id)
    assert obj == obj2


@requireCapability(dialect=In("mysql", "postgres"))
@pytest.mark.asyncio
async def test_list_contained_by(db):
    """Test JSON contained_by filter on list."""
    obj0 = await testmodels.JSONFields.create(data=["text"])
    obj1 = await testmodels.JSONFields.create(data=["tortoise", "msg"])
    obj2 = await testmodels.JSONFields.create(data=["tortoise"])
    obj3 = await testmodels.JSONFields.create(data=["new_message", "some_message"])
    objs = set(await testmodels.JSONFields.filter(data__contained_by=["text", "tortoise", "msg"]))
    created_objs = {obj0, obj1, obj2}
    assert created_objs == objs
    assert obj3 not in objs


@requireCapability(dialect=In("mysql", "postgres"))
@pytest.mark.asyncio
async def test_filter(db):
    """Test JSON filter with nested data."""
    obj0 = await testmodels.JSONFields.create(
        data={
            "breed": "labrador",
            "owner": {
                "name": "Bob",
                "last": None,
                "other_pets": [
                    {
                        "name": "Fishy",
                    }
                ],
            },
        }
    )
    obj1 = await testmodels.JSONFields.create(
        data={
            "breed": "husky",
            "owner": {
                "name": "Goldast",
                "last": None,
                "other_pets": [
                    {
                        "name": None,
                    }
                ],
            },
        }
    )
    obj = await testmodels.JSONFields.get(data__filter={"breed": "labrador"})
    obj2 = await testmodels.JSONFields.get(data__filter={"owner__name": "Goldast"})
    obj3 = await testmodels.JSONFields.get(data__filter={"owner__other_pets__0__name": "Fishy"})

    assert obj0 == obj
    assert obj1 == obj2
    assert obj0 == obj3

    with pytest.raises(DoesNotExist):
        await testmodels.JSONFields.get(data__filter={"breed": "NotFound"})
    with pytest.raises(DoesNotExist):
        await testmodels.JSONFields.get(data__filter={"owner__other_pets__0__name": "NotFound"})


@requireCapability(dialect=In("mysql", "postgres"))
@pytest.mark.asyncio
async def test_filter_not_condition(db):
    """Test JSON filter with not condition."""
    obj0 = await testmodels.JSONFields.create(
        data={
            "breed": "labrador",
            "owner": {
                "name": "Bob",
                "last": None,
                "other_pets": [
                    {
                        "name": "Fishy",
                    }
                ],
            },
        }
    )
    obj1 = await testmodels.JSONFields.create(
        data={
            "breed": "husky",
            "owner": {
                "name": "Goldast",
                "last": None,
                "other_pets": [
                    {
                        "name": "Fishy",
                    }
                ],
            },
        }
    )

    obj2 = await testmodels.JSONFields.get(data__filter={"breed__not": "husky"})
    obj3 = await testmodels.JSONFields.get(data__filter={"breed__not": "labrador"})
    assert obj0 == obj2
    assert obj1 == obj3


@requireCapability(dialect=In("mysql", "postgres"))
@pytest.mark.asyncio
async def test_filter_is_null_condition(db):
    """Test JSON filter with isnull condition."""
    obj0 = await testmodels.JSONFields.create(
        data={
            "breed": "labrador",
            "owner": {
                "name": "Boby",
                "last": "Cloud",
                "other_pets": [
                    {
                        "name": "Fishy",
                    }
                ],
            },
        }
    )

    obj1 = await testmodels.JSONFields.create(
        data={
            "breed": "labrador",
            "owner": {
                "name": None,
                "last": "Cloud",
                "other_pets": [
                    {
                        "name": "Fishy",
                    }
                ],
            },
        }
    )

    obj2 = await testmodels.JSONFields.get(data__filter={"owner__name__isnull": False})
    obj3 = await testmodels.JSONFields.get(data__filter={"owner__name__isnull": True})
    assert obj0 == obj2
    assert obj1 == obj3


@requireCapability(dialect=In("mysql", "postgres"))
@pytest.mark.asyncio
async def test_filter_not_is_null_condition(db):
    """Test JSON filter with not_isnull condition."""
    obj0 = await testmodels.JSONFields.create(
        data={
            "breed": "labrador",
            "owner": {
                "name": "Boby",
                "last": "Cloud",
                "other_pets": [
                    {
                        "name": "Fishy",
                    }
                ],
            },
        }
    )

    obj1 = await testmodels.JSONFields.create(
        data={
            "breed": "labrador",
            "owner": {
                "name": None,
                "last": "Cloud",
                "other_pets": [
                    {
                        "name": "Fishy",
                    }
                ],
            },
        }
    )

    obj2 = await testmodels.JSONFields.get(data__filter={"owner__name__not_isnull": True})
    obj3 = await testmodels.JSONFields.get(data__filter={"owner__name__not_isnull": False})
    assert obj0 == obj2
    assert obj1 == obj3


@pytest.mark.asyncio
async def test_values(db):
    """Test JSON field in values()."""
    obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})
    values = await testmodels.JSONFields.filter(id=obj0.id).values("data")
    assert values[0]["data"] == {"some": ["text", 3]}


@pytest.mark.asyncio
async def test_values_list(db):
    """Test JSON field in values_list()."""
    obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})
    values = await testmodels.JSONFields.filter(id=obj0.id).values_list("data", flat=True)
    assert values[0] == {"some": ["text", 3]}


def test_unique_fail():
    """Test that JSONField cannot be unique."""
    with pytest.raises(ConfigurationError, match="can't be indexed"):
        JSONField(unique=True)


def test_index_fail():
    """Test that JSONField cannot be indexed."""
    with pytest.raises(ConfigurationError, match="can't be indexed"):
        with pytest.warns(
            DeprecationWarning, match="`index` is deprecated, please use `db_index` instead"
        ):
            JSONField(index=True)
    with pytest.raises(ConfigurationError, match="can't be indexed"):
        JSONField(db_index=True)


@pytest.mark.asyncio
async def test_validate_str(db):
    """Test JSON field with validate from string."""
    obj0 = await testmodels.JSONFields.create(data=[], data_validate='["text", 5]')
    obj = await testmodels.JSONFields.get(id=obj0.id)
    assert obj.data_validate == ["text", 5]


@pytest.mark.asyncio
async def test_validate_dict(db):
    """Test JSON field with validate from dict."""
    obj0 = await testmodels.JSONFields.create(data=[], data_validate={"some": ["text", 3]})
    obj = await testmodels.JSONFields.get(id=obj0.id)
    assert obj.data_validate == {"some": ["text", 3]}


@pytest.mark.asyncio
async def test_validate_list(db):
    """Test JSON field with validate from list."""
    obj0 = await testmodels.JSONFields.create(data=[], data_validate=["text", 3])
    obj = await testmodels.JSONFields.get(id=obj0.id)
    assert obj.data_validate == ["text", 3]
