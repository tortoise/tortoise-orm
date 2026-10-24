import pytest

from tests import testmodels
from tortoise.exceptions import ValidationError
from tortoise.fields import BigIntField, IntField, SmallIntField


@pytest.mark.parametrize("field_cls", [SmallIntField, IntField, BigIntField])
def test_int_field_accepts_bounds(field_cls):
    field = field_cls()
    bounds = field.constraints
    for value in (bounds["ge"], 0, bounds["le"]):
        assert field.to_db_value(value, testmodels.IntFields) == value


@pytest.mark.parametrize("field_cls", [SmallIntField, IntField, BigIntField])
def test_int_field_rejects_out_of_range(field_cls):
    field = field_cls()
    field.model_field_name = "num"
    bounds = field.constraints
    for value in (bounds["ge"] - 1, bounds["le"] + 1):
        with pytest.raises(ValidationError, match="num: Value .* is out of range"):
            field.to_db_value(value, testmodels.IntFields)


def test_int_field_none_is_not_range_checked():
    field = IntField(null=True)
    assert field.to_db_value(None, testmodels.IntFields) is None


@pytest.mark.asyncio
async def test_save_out_of_range_raises(db):
    too_high = IntField().constraints["le"] + 1
    with pytest.raises(ValidationError, match="intnum"):
        await testmodels.IntFields.create(intnum=too_high)
    assert await testmodels.IntFields.all().count() == 0
