import pytest

from tests.testmodels import JSONFields
from tortoise.contrib.test import requireCapability
from tortoise.expressions import Connector, F


def test_arithmetic():
    """Test F expression arithmetic operations."""
    f = F("name")

    negated = -f
    assert negated.connector == Connector.mul
    assert negated.right.value == -1

    added = f + 1
    assert added.connector == Connector.add
    assert added.right.value == 1

    radded = 1 + f
    assert radded.connector == Connector.add
    assert radded.left.value == 1
    assert radded.right == f

    subbed = f - 1
    assert subbed.connector == Connector.sub
    assert subbed.right.value == 1

    rsubbed = 1 - f
    assert rsubbed.connector == Connector.sub
    assert rsubbed.left.value == 1

    mulled = f * 2
    assert mulled.connector == Connector.mul
    assert mulled.right.value == 2

    rmulled = 2 * f
    assert rmulled.connector == Connector.mul
    assert rmulled.left.value == 2

    divved = f / 2
    assert divved.connector == Connector.div
    assert divved.right.value == 2

    rdivved = 2 / f
    assert rdivved.connector == Connector.div
    assert rdivved.left.value == 2

    powed = f**2
    assert powed.connector == Connector.pow
    assert powed.right.value == 2

    rpowed = 2**f
    assert rpowed.connector == Connector.pow
    assert rpowed.left.value == 2

    modded = f % 2
    assert modded.connector == Connector.mod
    assert modded.right.value == 2

    rmodded = 2 % f
    assert rmodded.connector == Connector.mod
    assert rmodded.left.value == 2


@requireCapability(support_json_attributes=True)
@pytest.mark.asyncio
async def test_values_with_json_field_attribute(db):
    """Test F expression with JSON field attribute."""
    await JSONFields.create(data='{"attribute": 1}')
    res = await JSONFields.annotate(attribute=F("data__attribute")).first()
    assert int(res.attribute) == 1


@requireCapability(support_json_attributes=True)
@pytest.mark.asyncio
async def test_values_with_json_field_attribute_of_attribute(db):
    """Test F expression with nested JSON field attribute."""
    await JSONFields.create(data='{"attribute": {"subattribute": "value"}}')
    res = await JSONFields.annotate(subattribute=F("data__attribute__subattribute")).first()
    assert res.subattribute == "value"


@requireCapability(support_json_attributes=True)
@pytest.mark.asyncio
async def test_values_with_json_field_str_array_element(db):
    """Test F expression with JSON field string array element."""
    await JSONFields.create(data='["a", "b", "c"]')
    res = await JSONFields.annotate(array_element=F("data__0")).first()
    assert res.array_element == "a"
    res = await JSONFields.annotate(array_element=F("data__1")).first()
    assert res.array_element == "b"
    res = await JSONFields.annotate(array_element=F("data__2")).first()
    assert res.array_element == "c"
    res = await JSONFields.annotate(array_element=F("data__3")).first()
    assert res.array_element is None


@requireCapability(support_json_attributes=True)
@pytest.mark.asyncio
async def test_values_with_json_field_array_attribute(db):
    """Test F expression with JSON field array attribute."""
    await JSONFields.create(data='{"array": ["a", "b", "c"]}')
    res = await JSONFields.annotate(array_attribute=F("data__array__0")).first()
    assert res.array_attribute == "a"
    res = await JSONFields.annotate(array_attribute=F("data__array__1")).first()
    assert res.array_attribute == "b"
    res = await JSONFields.annotate(array_attribute=F("data__array__2")).first()
    assert res.array_attribute == "c"


@requireCapability(support_json_attributes=True)
@pytest.mark.asyncio
async def test_values_with_json_field_int_array_element(db):
    """
    Test F expression with JSON field integer array element.

    Among the supported dialects, only SQLite will return the correct type.
    """
    await JSONFields.create(data="[1, 2, 3]")
    res = await JSONFields.annotate(array_element=F("data__0")).first()
    assert int(res.array_element) == 1
    res = await JSONFields.annotate(array_element=F("data__1")).first()
    assert int(res.array_element) == 2
    res = await JSONFields.annotate(array_element=F("data__2")).first()
    assert int(res.array_element) == 3
    res = await JSONFields.annotate(array_element=F("data__3")).first()
    assert res.array_element is None


@requireCapability(support_json_attributes=True)
@pytest.mark.asyncio
async def test_filter_with_json_field_attribute(db):
    """Test F expression filter with JSON field attribute."""
    exp = await JSONFields.create(data='{"attribute": "a"}')
    res = await JSONFields.annotate(attribute=F("data__attribute")).filter(attribute="a").first()
    assert res.id == exp.id
    res = await JSONFields.annotate(attribute=F("data__attribute")).filter(attribute="b").first()
    assert res is None


@requireCapability(support_json_attributes=True)
@pytest.mark.asyncio
async def test_filter_with_json_field_attribute_of_attribute(db):
    """Test F expression filter with nested JSON field attribute."""
    exp = await JSONFields.create(data='{"attribute": {"subattribute": "value"}}')
    res = (
        await JSONFields.annotate(subattribute=F("data__attribute__subattribute"))
        .filter(subattribute="value")
        .first()
    )
    assert res.id == exp.id


@requireCapability(support_json_attributes=True)
@pytest.mark.asyncio
async def test_filter_with_json_field_str_array_element(db):
    """Test F expression filter with JSON field string array element."""
    exp = await JSONFields.create(data='["a", "b", "c"]')
    res = await JSONFields.annotate(array_element=F("data__0")).filter(array_element="a").first()
    assert res.id == exp.id
    res = await JSONFields.annotate(array_element=F("data__1")).filter(array_element="b").first()
    assert res.id == exp.id
