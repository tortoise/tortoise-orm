from decimal import Decimal
from enum import Enum

from tests.testmodels import (
    BooleanFields,
    CharFields,
    CharFkRelatedModel,
    CharPkModel,
    DecimalFields,
)
from tortoise.contrib import test
from tortoise.exceptions import FieldError
from tortoise.fields.base import StrEnum


class MyEnum(str, Enum):
    moo = "moo"


class MyStrEnum(StrEnum):
    moo = "moo"


class TestCharFieldFilters(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await CharFields.create(char="moo")
        await CharFields.create(char="baa", char_null="baa")
        await CharFields.create(char="oink")

    async def test_bad_param(self):
        with self.assertRaisesRegex(
            FieldError, "Unknown filter param 'charup'. Allowed base values are"
        ):
            await CharFields.filter(charup="moo")

    async def test_equal(self):
        self.assertEqual(
            set(await CharFields.filter(char="moo").values_list("char", flat=True)), {"moo"}
        )

    async def test_enum(self):
        self.assertEqual(
            set(await CharFields.filter(char=MyEnum.moo).values_list("char", flat=True)), {"moo"}
        )
        self.assertEqual(
            set(await CharFields.filter(char=MyStrEnum.moo).values_list("char", flat=True)), {"moo"}
        )

    async def test_not(self):
        self.assertEqual(
            set(await CharFields.filter(char__not="moo").values_list("char", flat=True)),
            {"baa", "oink"},
        )

    async def test_in(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__in=["moo", "baa"]).values_list("char", flat=True)),
            {"moo", "baa"},
        )

    async def test_in_empty(self):
        self.assertEqual(
            await CharFields.filter(char__in=[]).values_list("char", flat=True),
            [],
        )

    async def test_not_in(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__not_in=["moo", "baa"]).values_list("char", flat=True)
            ),
            {"oink"},
        )

    async def test_not_in_empty(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__not_in=[]).values_list("char", flat=True)),
            {"oink", "moo", "baa"},
        )

    async def test_isnull(self):
        self.assertSetEqual(
            set(await CharFields.filter(char_null__isnull=True).values_list("char", flat=True)),
            {"moo", "oink"},
        )
        self.assertSetEqual(
            set(await CharFields.filter(char_null__isnull=False).values_list("char", flat=True)),
            {"baa"},
        )

    async def test_not_isnull(self):
        self.assertSetEqual(
            set(await CharFields.filter(char_null__not_isnull=True).values_list("char", flat=True)),
            {"baa"},
        )
        self.assertSetEqual(
            set(
                await CharFields.filter(char_null__not_isnull=False).values_list("char", flat=True)
            ),
            {"moo", "oink"},
        )

    async def test_gte(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__gte="moo").values_list("char", flat=True)),
            {"moo", "oink"},
        )

    async def test_lte(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__lte="moo").values_list("char", flat=True)),
            {"moo", "baa"},
        )

    async def test_gt(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__gt="moo").values_list("char", flat=True)), {"oink"}
        )

    async def test_lt(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__lt="moo").values_list("char", flat=True)), {"baa"}
        )

    async def test_contains(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__contains="o").values_list("char", flat=True)),
            {"moo", "oink"},
        )

    async def test_startswith(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__startswith="m").values_list("char", flat=True)),
            {"moo"},
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__startswith="s").values_list("char", flat=True)), set()
        )

    async def test_endswith(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__endswith="o").values_list("char", flat=True)), {"moo"}
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__endswith="s").values_list("char", flat=True)), set()
        )

    async def test_icontains(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__icontains="oO").values_list("char", flat=True)),
            {"moo"},
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__icontains="Oo").values_list("char", flat=True)),
            {"moo"},
        )

    async def test_iexact(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__iexact="MoO").values_list("char", flat=True)), {"moo"}
        )

    async def test_istartswith(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__istartswith="m").values_list("char", flat=True)),
            {"moo"},
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__istartswith="M").values_list("char", flat=True)),
            {"moo"},
        )

    async def test_iendswith(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__iendswith="oO").values_list("char", flat=True)),
            {"moo"},
        )
        self.assertSetEqual(
            set(await CharFields.filter(char__iendswith="Oo").values_list("char", flat=True)),
            {"moo"},
        )

    async def test_sorting(self):
        self.assertEqual(
            await CharFields.all().order_by("char").values_list("char", flat=True),
            ["baa", "moo", "oink"],
        )


class TestBooleanFieldFilters(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await BooleanFields.create(boolean=True)
        await BooleanFields.create(boolean=False)
        await BooleanFields.create(boolean=True, boolean_null=True)
        await BooleanFields.create(boolean=False, boolean_null=True)
        await BooleanFields.create(boolean=True, boolean_null=False)
        await BooleanFields.create(boolean=False, boolean_null=False)

    async def test_equal_true(self):
        self.assertEqual(
            set(await BooleanFields.filter(boolean=True).values_list("boolean", "boolean_null")),
            {(True, None), (True, True), (True, False)},
        )

    async def test_equal_false(self):
        self.assertEqual(
            set(await BooleanFields.filter(boolean=False).values_list("boolean", "boolean_null")),
            {(False, None), (False, True), (False, False)},
        )

    async def test_equal_true2(self):
        self.assertEqual(
            set(
                await BooleanFields.filter(boolean_null=True).values_list("boolean", "boolean_null")
            ),
            {(False, True), (True, True)},
        )

    async def test_equal_false2(self):
        self.assertEqual(
            set(
                await BooleanFields.filter(boolean_null=False).values_list(
                    "boolean", "boolean_null"
                )
            ),
            {(False, False), (True, False)},
        )

    async def test_equal_null(self):
        self.assertEqual(
            set(
                await BooleanFields.filter(boolean_null=None).values_list("boolean", "boolean_null")
            ),
            {(False, None), (True, None)},
        )


class TestDecimalFieldFilters(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await DecimalFields.create(decimal="1.2345", decimal_nodec=1)
        await DecimalFields.create(decimal="2.34567", decimal_nodec=1)
        await DecimalFields.create(decimal="2.300", decimal_nodec=1)
        await DecimalFields.create(decimal="023.0", decimal_nodec=1)
        await DecimalFields.create(decimal="0.230", decimal_nodec=1)

    async def test_sorting(self):
        self.assertEqual(
            await DecimalFields.all().order_by("decimal").values_list("decimal", flat=True),
            [Decimal("0.23"), Decimal("1.2345"), Decimal("2.3"), Decimal("2.3457"), Decimal("23")],
        )

    async def test_gt(self):
        self.assertEqual(
            await DecimalFields.filter(decimal__gt=Decimal("1.2345"))
            .order_by("decimal")
            .values_list("decimal", flat=True),
            [Decimal("2.3"), Decimal("2.3457"), Decimal("23")],
        )

    async def test_between_and(self):
        self.assertEqual(
            await DecimalFields.filter(
                decimal__range=(Decimal("1.2344"), Decimal("1.2346"))
            ).values_list("decimal", flat=True),
            [Decimal("1.2345")],
        )

    async def test_in(self):
        self.assertEqual(
            await DecimalFields.filter(
                decimal__in=[Decimal("1.2345"), Decimal("1000")]
            ).values_list("decimal", flat=True),
            [Decimal("1.2345")],
        )


class TestCharFkFieldFilters(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        model1 = await CharPkModel.create(id=17)
        model2 = await CharPkModel.create(id=12)
        await CharPkModel.create(id=2001)
        await CharFkRelatedModel.create(model=model1)
        await CharFkRelatedModel.create(model=model1)
        await CharFkRelatedModel.create(model=model2)

    async def test_bad_param(self):
        with self.assertRaisesRegex(
            FieldError, "Unknown filter param 'bad_param'. Allowed base values are"
        ):
            await CharPkModel.filter(bad_param="moo")

    async def test_equal(self):
        self.assertEqual(
            set(await CharPkModel.filter(id=2001).values_list("id", flat=True)), {"2001"}
        )

    async def test_not(self):
        self.assertEqual(
            set(await CharPkModel.filter(id__not=2001).values_list("id", flat=True)),
            {"17", "12"},
        )

    async def test_in(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(id__in=[17, 12]).values_list("id", flat=True)),
            {"17", "12"},
        )

    async def test_in_empty(self):
        self.assertEqual(
            await CharPkModel.filter(id__in=[]).values_list("id", flat=True),
            [],
        )

    async def test_not_in(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(id__not_in=[17, 12]).values_list("id", flat=True)),
            {"2001"},
        )

    async def test_not_in_empty(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(id__not_in=[]).values_list("id", flat=True)),
            {"17", "12", "2001"},
        )

    async def test_isnull(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(children__isnull=True).values_list("id", flat=True)),
            {"2001"},
        )
        self.assertEqual(
            await CharPkModel.filter(children__isnull=False)
            .order_by("id")
            .values_list("id", flat=True),
            ["12", "17", "17"],
        )

    async def test_not_isnull(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(children__not_isnull=True).values_list("id", flat=True)),
            {"17", "12"},
        )
        self.assertSetEqual(
            set(await CharPkModel.filter(children__not_isnull=False).values_list("id", flat=True)),
            {"2001"},
        )

    async def test_gte(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(id__gte=17).values_list("id", flat=True)),
            {"17", "2001"},
        )

    async def test_lte(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(id__lte=17).values_list("id", flat=True)),
            {"12", "17"},
        )

    async def test_gt(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(id__gt=17).values_list("id", flat=True)), {"2001"}
        )

    async def test_lt(self):
        self.assertSetEqual(
            set(await CharPkModel.filter(id__lt=17).values_list("id", flat=True)), {"12"}
        )

    async def test_sorting(self):
        self.assertEqual(
            await CharPkModel.all().order_by("id").values_list("id", flat=True),
            ["12", "17", "2001"],
        )
        self.assertEqual(
            await CharPkModel.all().order_by("-id").values_list("id", flat=True),
            ["2001", "17", "12"],
        )
