from datetime import datetime
from decimal import Decimal

import pytest
import pytest_asyncio

from tests.testmodels import JSONFields
from tortoise.contrib import test
from tortoise.exceptions import DoesNotExist


async def get_by_data_filter(obj, **kwargs) -> JSONFields:
    return await JSONFields.get(data__filter=kwargs)


@pytest_asyncio.fixture
async def json_obj(db_postgres):
    """Create test object with JSON data for postgres tests."""
    obj = await JSONFields.create(
        data={
            "val": "word1",
            "int_val": 123,
            "float_val": 123.1,
            "date_val": datetime(1970, 1, 1, 12, 36, 59, 123456),
            "int_list": [1, 2, 3],
            "nested": {
                "val": "word2",
                "int_val": 456,
                "int_list": [4, 5, 6],
                "date_val": datetime(1970, 1, 1, 12, 36, 59, 123456),
                "nested": {
                    "val": "word3",
                },
            },
        }
    )
    return obj


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_json_in(json_obj):
    assert await get_by_data_filter(json_obj, val__in=["word1", "word2"]) == json_obj
    assert await get_by_data_filter(json_obj, val__not_in=["word3", "word4"]) == json_obj

    with pytest.raises(DoesNotExist):
        await get_by_data_filter(json_obj, val__in=["doesnotexist"])


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_json_defaults(json_obj):
    assert await get_by_data_filter(json_obj, val__not="word2") == json_obj
    assert await get_by_data_filter(json_obj, val__isnull=False) == json_obj
    assert await get_by_data_filter(json_obj, val__not_isnull=True) == json_obj


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_json_int_comparisons(json_obj):
    assert await get_by_data_filter(json_obj, int_val=123) == json_obj
    assert await get_by_data_filter(json_obj, int_val__gt=100) == json_obj
    assert await get_by_data_filter(json_obj, int_val__gte=100) == json_obj
    assert await get_by_data_filter(json_obj, int_val__lt=200) == json_obj
    assert await get_by_data_filter(json_obj, int_val__lte=200) == json_obj
    assert await get_by_data_filter(json_obj, int_val__range=[100, 200]) == json_obj

    with pytest.raises(DoesNotExist):
        await get_by_data_filter(json_obj, int_val__gt=1000)


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_json_float_comparisons(json_obj):
    assert await get_by_data_filter(json_obj, float_val__gt=100.0) == json_obj
    assert await get_by_data_filter(json_obj, float_val__gte=100.0) == json_obj
    assert await get_by_data_filter(json_obj, float_val__lt=200.0) == json_obj
    assert await get_by_data_filter(json_obj, float_val__lte=200.0) == json_obj
    assert await get_by_data_filter(json_obj, float_val__range=[100.0, 200.0]) == json_obj

    with pytest.raises(DoesNotExist):
        await get_by_data_filter(json_obj, int_val__gt=1000.0)


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_json_string_comparisons(json_obj):
    assert await get_by_data_filter(json_obj, val__contains="ord") == json_obj
    assert await get_by_data_filter(json_obj, val__icontains="OrD") == json_obj
    assert await get_by_data_filter(json_obj, val__startswith="wor") == json_obj
    assert await get_by_data_filter(json_obj, val__istartswith="wOr") == json_obj
    assert await get_by_data_filter(json_obj, val__endswith="rd1") == json_obj
    assert await get_by_data_filter(json_obj, val__iendswith="Rd1") == json_obj
    assert await get_by_data_filter(json_obj, val__iexact="wOrD1") == json_obj

    with pytest.raises(DoesNotExist):
        await get_by_data_filter(json_obj, val__contains="doesnotexist")


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_date_comparisons(json_obj):
    assert (
        await get_by_data_filter(json_obj, date_val=datetime(1970, 1, 1, 12, 36, 59, 123456))
        == json_obj
    )
    assert await get_by_data_filter(json_obj, date_val__year=1970) == json_obj
    assert await get_by_data_filter(json_obj, date_val__month=1) == json_obj
    assert await get_by_data_filter(json_obj, date_val__day=1) == json_obj
    assert await get_by_data_filter(json_obj, date_val__hour=12) == json_obj
    assert await get_by_data_filter(json_obj, date_val__minute=36) == json_obj
    assert await get_by_data_filter(json_obj, date_val__second=Decimal("59.123456")) == json_obj
    assert await get_by_data_filter(json_obj, date_val__microsecond=59123456) == json_obj


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_json_list(json_obj):
    assert await get_by_data_filter(json_obj, int_list__0__gt=0) == json_obj
    assert await get_by_data_filter(json_obj, int_list__0__lt=2) == json_obj

    with pytest.raises(DoesNotExist):
        await get_by_data_filter(json_obj, int_list__0__range=(20, 30))


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_nested(json_obj):
    assert await get_by_data_filter(json_obj, nested__val="word2") == json_obj
    assert await get_by_data_filter(json_obj, nested__int_val=456) == json_obj
    assert (
        await get_by_data_filter(
            json_obj, nested__date_val=datetime(1970, 1, 1, 12, 36, 59, 123456)
        )
        == json_obj
    )
    assert await get_by_data_filter(json_obj, nested__val__icontains="orD") == json_obj
    assert await get_by_data_filter(json_obj, nested__int_val__gte=400) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__year=1970) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__month=1) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__day=1) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__hour=12) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__minute=36) == json_obj
    assert (
        await get_by_data_filter(json_obj, nested__date_val__second=Decimal("59.123456"))
        == json_obj
    )
    assert await get_by_data_filter(json_obj, nested__date_val__microsecond=59123456) == json_obj
    assert await get_by_data_filter(json_obj, nested__val__iexact="wOrD2") == json_obj
    assert await get_by_data_filter(json_obj, nested__int_val__lt=500) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__year=1970) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__month=1) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__day=1) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__hour=12) == json_obj
    assert await get_by_data_filter(json_obj, nested__date_val__minute=36) == json_obj
    assert (
        await get_by_data_filter(json_obj, nested__date_val__second=Decimal("59.123456"))
        == json_obj
    )
    assert await get_by_data_filter(json_obj, nested__date_val__microsecond=59123456) == json_obj
    assert await get_by_data_filter(json_obj, nested__val__iexact="wOrD2") == json_obj


@test.requireCapability(dialect="postgres")
@pytest.mark.asyncio
async def test_nested_nested(json_obj):
    assert await get_by_data_filter(json_obj, nested__nested__val="word3") == json_obj
