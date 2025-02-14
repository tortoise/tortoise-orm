from decimal import Decimal

from tests import testmodels
from tortoise import fields
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, FieldError, IntegrityError
from tortoise.expressions import F
from tortoise.functions import Avg, Max, Sum


class TestDecimalFields(test.TestCase):
    def test_max_digits_empty(self):
        with self.assertRaisesRegex(
            TypeError,
            "missing 2 required positional arguments: 'max_digits' and 'decimal_places'",
        ):
            fields.DecimalField()  # pylint: disable=E1120

    def test_decimal_places_empty(self):
        with self.assertRaisesRegex(
            TypeError, "missing 1 required positional argument: 'decimal_places'"
        ):
            fields.DecimalField(max_digits=1)  # pylint: disable=E1120

    def test_max_fields_bad(self):
        with self.assertRaisesRegex(ConfigurationError, "'max_digits' must be >= 1"):
            fields.DecimalField(max_digits=0, decimal_places=2)

    def test_decimal_places_bad(self):
        with self.assertRaisesRegex(ConfigurationError, "'decimal_places' must be >= 0"):
            fields.DecimalField(max_digits=2, decimal_places=-1)

    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.DecimalFields.create()

    async def test_create(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal("1.23456"), decimal_nodec=18.7)
        obj = await testmodels.DecimalFields.get(id=obj0.id)
        self.assertEqual(obj.decimal, Decimal("1.2346"))
        self.assertEqual(obj.decimal_nodec, 19)
        self.assertEqual(obj.decimal_null, None)
        await obj.save()
        obj2 = await testmodels.DecimalFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_update(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal("1.23456"), decimal_nodec=18.7)
        await testmodels.DecimalFields.filter(id=obj0.id).update(decimal=Decimal("2.345"))
        obj = await testmodels.DecimalFields.get(id=obj0.id)
        self.assertEqual(obj.decimal, Decimal("2.345"))
        self.assertEqual(obj.decimal_nodec, 19)
        self.assertEqual(obj.decimal_null, None)

    async def test_filter(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal("1.23456"), decimal_nodec=18.7)
        obj = await testmodels.DecimalFields.filter(decimal=Decimal("1.2346")).first()
        self.assertEqual(obj, obj0)
        obj = (
            await testmodels.DecimalFields.annotate(d=F("decimal"))
            .filter(d=Decimal("1.2346"))
            .first()
        )
        self.assertEqual(obj, obj0)

    async def test_f_expression_update(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal("1.23456"), decimal_nodec=18.7)
        await obj0.filter(id=obj0.id).update(decimal=F("decimal") + Decimal("1"))
        obj1 = await testmodels.DecimalFields.get(id=obj0.id)
        self.assertEqual(obj1.decimal, Decimal("2.2346"))
        await obj0.filter(id=obj0.id).update(decimal=Decimal("1") - F("decimal"))
        obj1 = await testmodels.DecimalFields.get(id=obj0.id)
        self.assertEqual(obj1.decimal, Decimal("-1.2346"))

    async def test_values(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal("1.23456"), decimal_nodec=18.7)
        values = await testmodels.DecimalFields.get(id=obj0.id).values("decimal", "decimal_nodec")
        self.assertEqual(values["decimal"], Decimal("1.2346"))
        self.assertEqual(values["decimal_nodec"], 19)

    async def test_values_list(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal("1.23456"), decimal_nodec=18.7)
        values = await testmodels.DecimalFields.get(id=obj0.id).values_list(
            "decimal", "decimal_nodec"
        )
        self.assertEqual(list(values), [Decimal("1.2346"), 19])

    async def test_order_by(self):
        await testmodels.DecimalFields.create(decimal=Decimal("0"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("9.99"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("27.27"), decimal_nodec=1)
        values = (
            await testmodels.DecimalFields.all()
            .order_by("decimal")
            .values_list("decimal", flat=True)
        )
        self.assertEqual(values, [Decimal("0"), Decimal("9.99"), Decimal("27.27")])

    async def test_aggregate_sum(self):
        await testmodels.DecimalFields.create(decimal=Decimal("0"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("9.99"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("27.27"), decimal_nodec=1)
        values = (
            await testmodels.DecimalFields.all()
            .annotate(sum_decimal=Sum("decimal"))
            .values("sum_decimal")
        )
        self.assertEqual(
            values[0],
            {"sum_decimal": Decimal("37.26")},
        )

    async def test_aggregate_sum_with_f_expression(self):
        await testmodels.DecimalFields.create(decimal=Decimal("0"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("9.99"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("27.27"), decimal_nodec=1)
        values = (
            await testmodels.DecimalFields.all()
            .annotate(sum_decimal=Sum(F("decimal")))
            .values("sum_decimal")
        )
        self.assertEqual(
            values[0],
            {"sum_decimal": Decimal("37.26")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(sum_decimal=Sum(F("decimal") + 1))
            .values("sum_decimal")
        )
        self.assertEqual(
            values[0],
            {"sum_decimal": Decimal("40.26")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(sum_decimal=Sum(F("decimal") + F("decimal")))
            .values("sum_decimal")
        )
        self.assertEqual(
            values[0],
            {"sum_decimal": Decimal("74.52")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(sum_decimal=Sum(F("decimal") + F("decimal_nodec")))
            .values("sum_decimal")
        )
        self.assertEqual(
            values[0],
            {"sum_decimal": Decimal("4E+1")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(sum_decimal=Sum(F("decimal") + F("decimal_null")))
            .values("sum_decimal")
        )
        self.assertEqual(
            values[0],
            {"sum_decimal": None},
        )

    async def test_aggregate_sum_no_exist_field_with_f_expression(self):
        with self.assertRaisesRegex(
            FieldError,
            "There is no non-virtual field not_exist on Model DecimalFields",
        ):
            await (
                testmodels.DecimalFields.all()
                .annotate(sum_decimal=Sum(F("not_exist")))
                .values("sum_decimal")
            )

    async def test_aggregate_sum_different_field_type_at_right_with_f_expression(self):
        with self.assertRaisesRegex(
            FieldError, "Cannot use arithmetic expression between different field type"
        ):
            await (
                testmodels.DecimalFields.all()
                .annotate(sum_decimal=Sum(F("decimal") + F("id")))
                .values("sum_decimal")
            )

    async def test_aggregate_sum_different_field_type_at_left_with_f_expression(self):
        with self.assertRaisesRegex(
            FieldError, "Cannot use arithmetic expression between different field type"
        ):
            await (
                testmodels.DecimalFields.all()
                .annotate(sum_decimal=Sum(F("id") + F("decimal")))
                .values("sum_decimal")
            )

    async def test_aggregate_avg(self):
        await testmodels.DecimalFields.create(decimal=Decimal("0"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("9.99"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("27.27"), decimal_nodec=1)
        values = (
            await testmodels.DecimalFields.all()
            .annotate(avg_decimal=Avg("decimal"))
            .values("avg_decimal")
        )
        self.assertEqual(
            values[0],
            {"avg_decimal": Decimal("12.42")},
        )

    async def test_aggregate_avg_with_f_expression(self):
        await testmodels.DecimalFields.create(decimal=Decimal("0"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("9.99"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("27.27"), decimal_nodec=1)
        values = (
            await testmodels.DecimalFields.all()
            .annotate(avg_decimal=Avg(F("decimal")))
            .values("avg_decimal")
        )
        self.assertEqual(
            values[0],
            {"avg_decimal": Decimal("12.42")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(avg_decimal=Avg(F("decimal") + 1))
            .values("avg_decimal")
        )
        self.assertEqual(
            values[0],
            {"avg_decimal": Decimal("13.42")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(avg_decimal=Avg(F("decimal") + F("decimal")))
            .values("avg_decimal")
        )
        self.assertEqual(
            values[0],
            {"avg_decimal": Decimal("24.84")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(avg_decimal=Avg(F("decimal") + F("decimal_nodec")))
            .values("avg_decimal")
        )
        self.assertEqual(
            values[0],
            {"avg_decimal": Decimal("13")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(avg_decimal=Avg(F("decimal") + F("decimal_null")))
            .values("avg_decimal")
        )
        self.assertEqual(
            values[0],
            {"avg_decimal": None},
        )

    async def test_aggregate_max(self):
        await testmodels.DecimalFields.create(decimal=Decimal("0"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("9.99"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("27.27"), decimal_nodec=1)
        values = (
            await testmodels.DecimalFields.all()
            .annotate(max_decimal=Max("decimal"))
            .values("max_decimal")
        )
        self.assertEqual(
            values[0],
            {"max_decimal": Decimal("27.27")},
        )

    async def test_aggregate_max_with_f_expression(self):
        await testmodels.DecimalFields.create(decimal=Decimal("0"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("9.99"), decimal_nodec=1)
        await testmodels.DecimalFields.create(decimal=Decimal("27.27"), decimal_nodec=1)
        values = (
            await testmodels.DecimalFields.all()
            .annotate(max_decimal=Max(F("decimal")))
            .values("max_decimal")
        )
        self.assertEqual(
            values[0],
            {"max_decimal": Decimal("27.27")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(max_decimal=Max(F("decimal") + 1))
            .values("max_decimal")
        )
        self.assertEqual(
            values[0],
            {"max_decimal": Decimal("28.27")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(max_decimal=Max(F("decimal") + F("decimal")))
            .values("max_decimal")
        )
        self.assertEqual(
            values[0],
            {"max_decimal": Decimal("54.54")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(max_decimal=Max(F("decimal") + F("decimal_nodec")))
            .values("max_decimal")
        )
        self.assertEqual(
            values[0],
            {"max_decimal": Decimal("28")},
        )

        values = (
            await testmodels.DecimalFields.all()
            .annotate(max_decimal=Max(F("decimal") + F("decimal_null")))
            .values("max_decimal")
        )
        self.assertEqual(
            values[0],
            {"max_decimal": None},
        )
