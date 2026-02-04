import pytest

from tests import testmodels_postgres as testmodels
from tortoise.contrib.test import requireCapability
from tortoise.exceptions import IntegrityError


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_empty(db_array_fields):
    """Test that creating without required array field raises IntegrityError."""
    with pytest.raises(IntegrityError):
        await testmodels.ArrayFields.create()


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_create(db_array_fields):
    """Test array field creation and retrieval."""
    obj0 = await testmodels.ArrayFields.create(array=[0])
    obj = await testmodels.ArrayFields.get(id=obj0.id)
    assert obj.array == [0]
    assert obj.array_null is None
    await obj.save()
    obj2 = await testmodels.ArrayFields.get(id=obj.id)
    assert obj == obj2


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_update(db_array_fields):
    """Test array field update."""
    obj0 = await testmodels.ArrayFields.create(array=[0])
    await testmodels.ArrayFields.filter(id=obj0.id).update(array=[1])
    obj = await testmodels.ArrayFields.get(id=obj0.id)
    assert obj.array == [1]
    assert obj.array_null is None


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_values(db_array_fields):
    """Test array field in values()."""
    obj0 = await testmodels.ArrayFields.create(array=[0])
    values = await testmodels.ArrayFields.get(id=obj0.id).values("array")
    assert values["array"] == [0]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_values_list(db_array_fields):
    """Test array field in values_list()."""
    obj0 = await testmodels.ArrayFields.create(array=[0])
    values = await testmodels.ArrayFields.get(id=obj0.id).values_list("array", flat=True)
    assert values == [0]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_eq_filter(db_array_fields):
    """Test equality filter on array field."""
    obj1 = await testmodels.ArrayFields.create(array=[1, 2, 3])
    obj2 = await testmodels.ArrayFields.create(array=[1, 2])

    found = await testmodels.ArrayFields.filter(array=[1, 2, 3]).first()
    assert found == obj1

    found = await testmodels.ArrayFields.filter(array=[1, 2]).first()
    assert found == obj2


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_not_filter(db_array_fields):
    """Test not filter on array field."""
    await testmodels.ArrayFields.create(array=[1, 2, 3])
    obj2 = await testmodels.ArrayFields.create(array=[1, 2])

    found = await testmodels.ArrayFields.filter(array__not=[1, 2, 3]).first()
    assert found == obj2


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_contains_ints(db_array_fields):
    """Test contains filter on integer array field."""
    obj1 = await testmodels.ArrayFields.create(array=[1, 2, 3])
    obj2 = await testmodels.ArrayFields.create(array=[2, 3])
    await testmodels.ArrayFields.create(array=[4, 5, 6])

    found = await testmodels.ArrayFields.filter(array__contains=[2])
    assert found == [obj1, obj2]

    found = await testmodels.ArrayFields.filter(array__contains=[10])
    assert found == []


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_contains_smallints(db_array_fields):
    """Test contains filter on smallint array field."""
    obj1 = await testmodels.ArrayFields.create(array=[], array_smallint=[1, 2, 3])

    found = await testmodels.ArrayFields.filter(array_smallint__contains=[2]).first()
    assert found == obj1


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_contains_strs(db_array_fields):
    """Test contains filter on string array field."""
    obj1 = await testmodels.ArrayFields.create(array_str=["a", "b", "c"], array=[])

    found = await testmodels.ArrayFields.filter(array_str__contains=["a", "b", "c"])
    assert found == [obj1]

    found = await testmodels.ArrayFields.filter(array_str__contains=["a", "b"])
    assert found == [obj1]

    found = await testmodels.ArrayFields.filter(array_str__contains=["a", "b", "c", "d"])
    assert found == []


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_contained_by_ints(db_array_fields):
    """Test contained_by filter on integer array field."""
    obj1 = await testmodels.ArrayFields.create(array=[1])
    obj2 = await testmodels.ArrayFields.create(array=[1, 2])
    obj3 = await testmodels.ArrayFields.create(array=[1, 2, 3])

    found = await testmodels.ArrayFields.filter(array__contained_by=[1, 2, 3])
    assert found == [obj1, obj2, obj3]

    found = await testmodels.ArrayFields.filter(array__contained_by=[1, 2])
    assert found == [obj1, obj2]

    found = await testmodels.ArrayFields.filter(array__contained_by=[1])
    assert found == [obj1]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_contained_by_strs(db_array_fields):
    """Test contained_by filter on string array field."""
    obj1 = await testmodels.ArrayFields.create(array_str=["a"], array=[])
    obj2 = await testmodels.ArrayFields.create(array_str=["a", "b"], array=[])
    obj3 = await testmodels.ArrayFields.create(array_str=["a", "b", "c"], array=[])

    found = await testmodels.ArrayFields.filter(array_str__contained_by=["a", "b", "c", "d"])
    assert found == [obj1, obj2, obj3]

    found = await testmodels.ArrayFields.filter(array_str__contained_by=["a", "b"])
    assert found == [obj1, obj2]

    found = await testmodels.ArrayFields.filter(array_str__contained_by=["x", "y", "z"])
    assert found == []


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_overlap_ints(db_array_fields):
    """Test overlap filter on integer array field."""
    obj1 = await testmodels.ArrayFields.create(array=[1, 2, 3])
    obj2 = await testmodels.ArrayFields.create(array=[2, 3, 4])
    obj3 = await testmodels.ArrayFields.create(array=[3, 4, 5])

    found = await testmodels.ArrayFields.filter(array__overlap=[1, 2])
    assert found == [obj1, obj2]

    found = await testmodels.ArrayFields.filter(array__overlap=[4])
    assert found == [obj2, obj3]

    found = await testmodels.ArrayFields.filter(array__overlap=[1, 2, 3, 4, 5])
    assert found == [obj1, obj2, obj3]


@requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_array_length(db_array_fields):
    """Test array length filter."""
    await testmodels.ArrayFields.create(array=[1, 2, 3])
    await testmodels.ArrayFields.create(array=[1])
    await testmodels.ArrayFields.create(array=[1, 2])

    found = await testmodels.ArrayFields.filter(array__len=3).values_list("array", flat=True)
    assert list(found) == [[1, 2, 3]]

    found = await testmodels.ArrayFields.filter(array__len=1).values_list("array", flat=True)
    assert list(found) == [[1]]

    found = await testmodels.ArrayFields.filter(array__len=0).values_list("array", flat=True)
    assert list(found) == []
