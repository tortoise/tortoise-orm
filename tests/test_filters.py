from decimal import Decimal
from enum import Enum

import pytest
import pytest_asyncio

from tests.testmodels import (
    BooleanFields,
    CharFields,
    CharFkRelatedModel,
    CharPkModel,
    DecimalFields,
)
from tortoise.exceptions import FieldError
from tortoise.fields.base import StrEnum


class MyEnum(str, Enum):
    moo = "moo"


class MyStrEnum(StrEnum):
    moo = "moo"


# --- CharFields tests ---


@pytest_asyncio.fixture
async def char_fields_data(db):
    await CharFields.create(char="moo")
    await CharFields.create(char="baa", char_null="baa")
    await CharFields.create(char="oink")


@pytest.mark.asyncio
async def test_char_field_bad_param(db, char_fields_data):
    with pytest.raises(FieldError, match="Unknown filter param 'charup'. Allowed base values are"):
        await CharFields.filter(charup="moo")


@pytest.mark.asyncio
async def test_char_field_equal(db, char_fields_data):
    assert set(await CharFields.filter(char="moo").values_list("char", flat=True)) == {"moo"}


@pytest.mark.asyncio
async def test_char_field_enum(db, char_fields_data):
    assert set(await CharFields.filter(char=MyEnum.moo).values_list("char", flat=True)) == {"moo"}
    assert set(await CharFields.filter(char=MyStrEnum.moo).values_list("char", flat=True)) == {
        "moo"
    }


@pytest.mark.asyncio
async def test_char_field_not(db, char_fields_data):
    assert set(await CharFields.filter(char__not="moo").values_list("char", flat=True)) == {
        "baa",
        "oink",
    }


@pytest.mark.asyncio
async def test_char_field_in(db, char_fields_data):
    assert set(await CharFields.filter(char__in=["moo", "baa"]).values_list("char", flat=True)) == {
        "moo",
        "baa",
    }


@pytest.mark.asyncio
async def test_char_field_in_empty(db, char_fields_data):
    assert await CharFields.filter(char__in=[]).values_list("char", flat=True) == []


@pytest.mark.asyncio
async def test_char_field_not_in(db, char_fields_data):
    assert set(
        await CharFields.filter(char__not_in=["moo", "baa"]).values_list("char", flat=True)
    ) == {"oink"}


@pytest.mark.asyncio
async def test_char_field_not_in_empty(db, char_fields_data):
    assert set(await CharFields.filter(char__not_in=[]).values_list("char", flat=True)) == {
        "oink",
        "moo",
        "baa",
    }


@pytest.mark.asyncio
async def test_char_field_isnull(db, char_fields_data):
    assert set(await CharFields.filter(char_null__isnull=True).values_list("char", flat=True)) == {
        "moo",
        "oink",
    }
    assert set(await CharFields.filter(char_null__isnull=False).values_list("char", flat=True)) == {
        "baa"
    }


@pytest.mark.asyncio
async def test_char_field_not_isnull(db, char_fields_data):
    assert set(
        await CharFields.filter(char_null__not_isnull=True).values_list("char", flat=True)
    ) == {"baa"}
    assert set(
        await CharFields.filter(char_null__not_isnull=False).values_list("char", flat=True)
    ) == {"moo", "oink"}


@pytest.mark.asyncio
async def test_char_field_gte(db, char_fields_data):
    assert set(await CharFields.filter(char__gte="moo").values_list("char", flat=True)) == {
        "moo",
        "oink",
    }


@pytest.mark.asyncio
async def test_char_field_lte(db, char_fields_data):
    assert set(await CharFields.filter(char__lte="moo").values_list("char", flat=True)) == {
        "moo",
        "baa",
    }


@pytest.mark.asyncio
async def test_char_field_gt(db, char_fields_data):
    assert set(await CharFields.filter(char__gt="moo").values_list("char", flat=True)) == {"oink"}


@pytest.mark.asyncio
async def test_char_field_lt(db, char_fields_data):
    assert set(await CharFields.filter(char__lt="moo").values_list("char", flat=True)) == {"baa"}


@pytest.mark.asyncio
async def test_char_field_contains(db, char_fields_data):
    assert set(await CharFields.filter(char__contains="o").values_list("char", flat=True)) == {
        "moo",
        "oink",
    }


@pytest.mark.asyncio
async def test_char_field_startswith(db, char_fields_data):
    assert set(await CharFields.filter(char__startswith="m").values_list("char", flat=True)) == {
        "moo"
    }
    assert (
        set(await CharFields.filter(char__startswith="s").values_list("char", flat=True)) == set()
    )


@pytest.mark.asyncio
async def test_char_field_endswith(db, char_fields_data):
    assert set(await CharFields.filter(char__endswith="o").values_list("char", flat=True)) == {
        "moo"
    }
    assert set(await CharFields.filter(char__endswith="s").values_list("char", flat=True)) == set()


@pytest.mark.asyncio
async def test_char_field_icontains(db, char_fields_data):
    assert set(await CharFields.filter(char__icontains="oO").values_list("char", flat=True)) == {
        "moo"
    }
    assert set(await CharFields.filter(char__icontains="Oo").values_list("char", flat=True)) == {
        "moo"
    }


@pytest.mark.asyncio
async def test_char_field_iexact(db, char_fields_data):
    assert set(await CharFields.filter(char__iexact="MoO").values_list("char", flat=True)) == {
        "moo"
    }


@pytest.mark.asyncio
async def test_char_field_istartswith(db, char_fields_data):
    assert set(await CharFields.filter(char__istartswith="m").values_list("char", flat=True)) == {
        "moo"
    }
    assert set(await CharFields.filter(char__istartswith="M").values_list("char", flat=True)) == {
        "moo"
    }


@pytest.mark.asyncio
async def test_char_field_iendswith(db, char_fields_data):
    assert set(await CharFields.filter(char__iendswith="oO").values_list("char", flat=True)) == {
        "moo"
    }
    assert set(await CharFields.filter(char__iendswith="Oo").values_list("char", flat=True)) == {
        "moo"
    }


@pytest.mark.asyncio
async def test_char_field_sorting(db, char_fields_data):
    assert await CharFields.all().order_by("char").values_list("char", flat=True) == [
        "baa",
        "moo",
        "oink",
    ]


# --- BooleanFields tests ---


@pytest_asyncio.fixture
async def boolean_fields_data(db):
    await BooleanFields.create(boolean=True)
    await BooleanFields.create(boolean=False)
    await BooleanFields.create(boolean=True, boolean_null=True)
    await BooleanFields.create(boolean=False, boolean_null=True)
    await BooleanFields.create(boolean=True, boolean_null=False)
    await BooleanFields.create(boolean=False, boolean_null=False)


@pytest.mark.asyncio
async def test_boolean_field_equal_true(db, boolean_fields_data):
    assert set(await BooleanFields.filter(boolean=True).values_list("boolean", "boolean_null")) == {
        (True, None),
        (True, True),
        (True, False),
    }


@pytest.mark.asyncio
async def test_boolean_field_equal_false(db, boolean_fields_data):
    assert set(
        await BooleanFields.filter(boolean=False).values_list("boolean", "boolean_null")
    ) == {(False, None), (False, True), (False, False)}


@pytest.mark.asyncio
async def test_boolean_field_equal_true2(db, boolean_fields_data):
    assert set(
        await BooleanFields.filter(boolean_null=True).values_list("boolean", "boolean_null")
    ) == {(False, True), (True, True)}


@pytest.mark.asyncio
async def test_boolean_field_equal_false2(db, boolean_fields_data):
    assert set(
        await BooleanFields.filter(boolean_null=False).values_list("boolean", "boolean_null")
    ) == {(False, False), (True, False)}


@pytest.mark.asyncio
async def test_boolean_field_equal_null(db, boolean_fields_data):
    assert set(
        await BooleanFields.filter(boolean_null=None).values_list("boolean", "boolean_null")
    ) == {(False, None), (True, None)}


# --- DecimalFields tests ---


@pytest_asyncio.fixture
async def decimal_fields_data(db):
    await DecimalFields.create(decimal="1.2345", decimal_nodec=1)
    await DecimalFields.create(decimal="2.34567", decimal_nodec=1)
    await DecimalFields.create(decimal="2.300", decimal_nodec=1)
    await DecimalFields.create(decimal="023.0", decimal_nodec=1)
    await DecimalFields.create(decimal="0.230", decimal_nodec=1)


@pytest.mark.asyncio
async def test_decimal_field_sorting(db, decimal_fields_data):
    assert await DecimalFields.all().order_by("decimal").values_list("decimal", flat=True) == [
        Decimal("0.23"),
        Decimal("1.2345"),
        Decimal("2.3"),
        Decimal("2.3457"),
        Decimal("23"),
    ]


@pytest.mark.asyncio
async def test_decimal_field_gt(db, decimal_fields_data):
    assert await DecimalFields.filter(decimal__gt=Decimal("1.2345")).order_by(
        "decimal"
    ).values_list("decimal", flat=True) == [Decimal("2.3"), Decimal("2.3457"), Decimal("23")]


@pytest.mark.asyncio
async def test_decimal_field_between_and(db, decimal_fields_data):
    assert await DecimalFields.filter(
        decimal__range=(Decimal("1.2344"), Decimal("1.2346"))
    ).values_list("decimal", flat=True) == [Decimal("1.2345")]


@pytest.mark.asyncio
async def test_decimal_field_in(db, decimal_fields_data):
    assert await DecimalFields.filter(decimal__in=[Decimal("1.2345"), Decimal("1000")]).values_list(
        "decimal", flat=True
    ) == [Decimal("1.2345")]


# --- CharPkModel / CharFkRelatedModel tests ---


@pytest_asyncio.fixture
async def char_fk_data(db):
    model1 = await CharPkModel.create(id=17)
    model2 = await CharPkModel.create(id=12)
    await CharPkModel.create(id=2001)
    await CharFkRelatedModel.create(model=model1)
    await CharFkRelatedModel.create(model=model1)
    await CharFkRelatedModel.create(model=model2)


@pytest.mark.asyncio
async def test_char_fk_bad_param(db, char_fk_data):
    with pytest.raises(
        FieldError, match="Unknown filter param 'bad_param'. Allowed base values are"
    ):
        await CharPkModel.filter(bad_param="moo")


@pytest.mark.asyncio
async def test_char_fk_equal(db, char_fk_data):
    assert set(await CharPkModel.filter(id=2001).values_list("id", flat=True)) == {"2001"}


@pytest.mark.asyncio
async def test_char_fk_not(db, char_fk_data):
    assert set(await CharPkModel.filter(id__not=2001).values_list("id", flat=True)) == {"17", "12"}


@pytest.mark.asyncio
async def test_char_fk_in(db, char_fk_data):
    assert set(await CharPkModel.filter(id__in=[17, 12]).values_list("id", flat=True)) == {
        "17",
        "12",
    }


@pytest.mark.asyncio
async def test_char_fk_in_empty(db, char_fk_data):
    assert await CharPkModel.filter(id__in=[]).values_list("id", flat=True) == []


@pytest.mark.asyncio
async def test_char_fk_not_in(db, char_fk_data):
    assert set(await CharPkModel.filter(id__not_in=[17, 12]).values_list("id", flat=True)) == {
        "2001"
    }


@pytest.mark.asyncio
async def test_char_fk_not_in_empty(db, char_fk_data):
    assert set(await CharPkModel.filter(id__not_in=[]).values_list("id", flat=True)) == {
        "17",
        "12",
        "2001",
    }


@pytest.mark.asyncio
async def test_char_fk_isnull(db, char_fk_data):
    assert set(await CharPkModel.filter(children__isnull=True).values_list("id", flat=True)) == {
        "2001"
    }
    assert await CharPkModel.filter(children__isnull=False).order_by("id").values_list(
        "id", flat=True
    ) == ["12", "17", "17"]


@pytest.mark.asyncio
async def test_char_fk_not_isnull(db, char_fk_data):
    assert set(
        await CharPkModel.filter(children__not_isnull=True).values_list("id", flat=True)
    ) == {"17", "12"}
    assert set(
        await CharPkModel.filter(children__not_isnull=False).values_list("id", flat=True)
    ) == {"2001"}


@pytest.mark.asyncio
async def test_char_fk_gte(db, char_fk_data):
    assert set(await CharPkModel.filter(id__gte=17).values_list("id", flat=True)) == {"17", "2001"}


@pytest.mark.asyncio
async def test_char_fk_lte(db, char_fk_data):
    assert set(await CharPkModel.filter(id__lte=17).values_list("id", flat=True)) == {"12", "17"}


@pytest.mark.asyncio
async def test_char_fk_gt(db, char_fk_data):
    assert set(await CharPkModel.filter(id__gt=17).values_list("id", flat=True)) == {"2001"}


@pytest.mark.asyncio
async def test_char_fk_lt(db, char_fk_data):
    assert set(await CharPkModel.filter(id__lt=17).values_list("id", flat=True)) == {"12"}


@pytest.mark.asyncio
async def test_char_fk_sorting(db, char_fk_data):
    assert await CharPkModel.all().order_by("id").values_list("id", flat=True) == [
        "12",
        "17",
        "2001",
    ]
    assert await CharPkModel.all().order_by("-id").values_list("id", flat=True) == [
        "2001",
        "17",
        "12",
    ]
