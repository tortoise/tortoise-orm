from decimal import Decimal

from tortoise.contrib import test
from tortoise.exceptions import FieldError
from tortoise.tests.testmodels import (
    BooleanFields,
    CharFields,
    DecimalFields,
    RaceParticipant,
    RacePlacingEnum,
)


class TestCharFieldFilters(test.TestCase):
    async def setUp(self):
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
            set(await CharFields.filter(char="moo").values_list("char", flat=True)),
            {"moo"},
        )

    async def test_not(self):
        self.assertEqual(
            set(
                await CharFields.filter(char__not="moo").values_list("char", flat=True)
            ),
            {"baa", "oink"},
        )

    async def test_in(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__in=["moo", "baa"]).values_list(
                    "char", flat=True
                )
            ),
            {"moo", "baa"},
        )

    async def test_not_in(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__not_in=["moo", "baa"]).values_list(
                    "char", flat=True
                )
            ),
            {"oink"},
        )

    async def test_isnull(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char_null__isnull=True).values_list(
                    "char", flat=True
                )
            ),
            {"moo", "oink"},
        )
        self.assertSetEqual(
            set(
                await CharFields.filter(char_null__isnull=False).values_list(
                    "char", flat=True
                )
            ),
            {"baa"},
        )

    async def test_not_isnull(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char_null__not_isnull=True).values_list(
                    "char", flat=True
                )
            ),
            {"baa"},
        )
        self.assertSetEqual(
            set(
                await CharFields.filter(char_null__not_isnull=False).values_list(
                    "char", flat=True
                )
            ),
            {"moo", "oink"},
        )

    async def test_gte(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__gte="moo").values_list("char", flat=True)
            ),
            {"moo", "oink"},
        )

    async def test_lte(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__lte="moo").values_list("char", flat=True)
            ),
            {"moo", "baa"},
        )

    async def test_gt(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__gt="moo").values_list("char", flat=True)),
            {"oink"},
        )

    async def test_lt(self):
        self.assertSetEqual(
            set(await CharFields.filter(char__lt="moo").values_list("char", flat=True)),
            {"baa"},
        )

    async def test_contains(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__contains="o").values_list(
                    "char", flat=True
                )
            ),
            {"moo", "oink"},
        )

    async def test_startswith(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__startswith="m").values_list(
                    "char", flat=True
                )
            ),
            {"moo"},
        )
        self.assertSetEqual(
            set(
                await CharFields.filter(char__startswith="s").values_list(
                    "char", flat=True
                )
            ),
            set(),
        )

    async def test_endswith(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__endswith="o").values_list(
                    "char", flat=True
                )
            ),
            {"moo"},
        )
        self.assertSetEqual(
            set(
                await CharFields.filter(char__endswith="s").values_list(
                    "char", flat=True
                )
            ),
            set(),
        )

    async def test_icontains(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__icontains="oO").values_list(
                    "char", flat=True
                )
            ),
            {"moo"},
        )
        self.assertSetEqual(
            set(
                await CharFields.filter(char__icontains="Oo").values_list(
                    "char", flat=True
                )
            ),
            {"moo"},
        )

    async def test_istartswith(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__istartswith="m").values_list(
                    "char", flat=True
                )
            ),
            {"moo"},
        )
        self.assertSetEqual(
            set(
                await CharFields.filter(char__istartswith="M").values_list(
                    "char", flat=True
                )
            ),
            {"moo"},
        )

    async def test_iendswith(self):
        self.assertSetEqual(
            set(
                await CharFields.filter(char__iendswith="oO").values_list(
                    "char", flat=True
                )
            ),
            {"moo"},
        )
        self.assertSetEqual(
            set(
                await CharFields.filter(char__iendswith="Oo").values_list(
                    "char", flat=True
                )
            ),
            {"moo"},
        )

    async def test_sorting(self):
        self.assertEqual(
            await CharFields.all().order_by("char").values_list("char", flat=True),
            ["baa", "moo", "oink"],
        )


class TestBooleanFieldFilters(test.TestCase):
    async def setUp(self):
        await BooleanFields.create(boolean=True)
        await BooleanFields.create(boolean=False)
        await BooleanFields.create(boolean=True, boolean_null=True)
        await BooleanFields.create(boolean=False, boolean_null=True)
        await BooleanFields.create(boolean=True, boolean_null=False)
        await BooleanFields.create(boolean=False, boolean_null=False)

    async def test_equal_true(self):
        self.assertEqual(
            set(
                await BooleanFields.filter(boolean=True).values_list(
                    "boolean", "boolean_null"
                )
            ),
            {(True, None), (True, True), (True, False)},
        )

    async def test_equal_false(self):
        self.assertEqual(
            set(
                await BooleanFields.filter(boolean=False).values_list(
                    "boolean", "boolean_null"
                )
            ),
            {(False, None), (False, True), (False, False)},
        )

    async def test_equal_true2(self):
        self.assertEqual(
            set(
                await BooleanFields.filter(boolean_null=True).values_list(
                    "boolean", "boolean_null"
                )
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
                await BooleanFields.filter(boolean_null=None).values_list(
                    "boolean", "boolean_null"
                )
            ),
            {(False, None), (True, None)},
        )


class TestDecimalFieldFilters(test.TestCase):
    async def setUp(self):
        await DecimalFields.create(decimal="1.2345", decimal_nodec=1)
        await DecimalFields.create(decimal="2.34567", decimal_nodec=1)
        await DecimalFields.create(decimal="2.300", decimal_nodec=1)
        await DecimalFields.create(decimal="023.0", decimal_nodec=1)
        await DecimalFields.create(decimal="0.230", decimal_nodec=1)

    async def test_sorting(self):
        self.assertEqual(
            await DecimalFields.all()
            .order_by("decimal")
            .values_list("decimal", flat=True),
            [
                Decimal("0.23"),
                Decimal("1.2345"),
                Decimal("2.3"),
                Decimal("2.3457"),
                Decimal("23"),
            ],
        )

    async def test_gt(self):
        self.assertEqual(
            await DecimalFields.filter(decimal__gt=Decimal("1.2345"))
            .order_by("decimal")
            .values_list("decimal", flat=True),
            [Decimal("2.3"), Decimal("2.3457"), Decimal("23")],
        )


class TestCustomFieldFilters(test.TestCase):
    async def setUp(self):
        await RaceParticipant.create(
            first_name="George",
            place=RacePlacingEnum.FIRST,
            predicted_place=RacePlacingEnum.SECOND,
        )
        await RaceParticipant.create(
            first_name="John",
            place=RacePlacingEnum.SECOND,
            predicted_place=RacePlacingEnum.THIRD,
        )
        await RaceParticipant.create(first_name="Paul", place=RacePlacingEnum.THIRD)
        await RaceParticipant.create(
            first_name="Ringo", place=RacePlacingEnum.RUNNER_UP
        )
        await RaceParticipant.create(
            first_name="Stuart", predicted_place=RacePlacingEnum.FIRST
        )

    async def test_equal(self):
        self.assertEqual(
            set(
                await RaceParticipant.filter(place=RacePlacingEnum.FIRST).values_list(
                    "place", flat=True
                )
            ),
            {RacePlacingEnum.FIRST},
        )

    async def test_not(self):
        self.assertEqual(
            set(
                await RaceParticipant.filter(
                    place__not=RacePlacingEnum.FIRST
                ).values_list("place", flat=True)
            ),
            {
                RacePlacingEnum.SECOND,
                RacePlacingEnum.THIRD,
                RacePlacingEnum.RUNNER_UP,
                RacePlacingEnum.DNF,
            },
        )

    async def test_in(self):
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(
                    place__in=[RacePlacingEnum.DNF, RacePlacingEnum.RUNNER_UP]
                ).values_list("place", flat=True)
            ),
            {RacePlacingEnum.DNF, RacePlacingEnum.RUNNER_UP},
        )

    async def test_not_in(self):
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(
                    place__not_in=[RacePlacingEnum.DNF, RacePlacingEnum.RUNNER_UP]
                ).values_list("place", flat=True)
            ),
            {RacePlacingEnum.FIRST, RacePlacingEnum.SECOND, RacePlacingEnum.THIRD},
        )

    async def test_isnull(self):
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(predicted_place__isnull=True).values_list(
                    "first_name", flat=True
                )
            ),
            {"Paul", "Ringo"},
        )
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(predicted_place__isnull=False).values_list(
                    "first_name", flat=True
                )
            ),
            {"George", "John", "Stuart"},
        )

    async def test_not_isnull(self):
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(
                    predicted_place__not_isnull=False
                ).values_list("first_name", flat=True)
            ),
            {"Paul", "Ringo"},
        )
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(
                    predicted_place__not_isnull=True
                ).values_list("first_name", flat=True)
            ),
            {"George", "John", "Stuart"},
        )
