from decimal import Decimal

from tortoise import fields
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.tests import testmodels


class TestDecimalFields(test.TestCase):
    def test_max_digits_empty(self):
        with self.assertRaisesRegex(
            TypeError,
            "missing 2 required positional arguments: 'max_digits' and" " 'decimal_places'",
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

    async def test_values(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal("1.23456"), decimal_nodec=18.7)
        values = await testmodels.DecimalFields.get(id=obj0.id).values("decimal", "decimal_nodec")
        self.assertEqual(values[0]["decimal"], Decimal("1.2346"))
        self.assertEqual(values[0]["decimal_nodec"], 19)

    async def test_values_list(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal("1.23456"), decimal_nodec=18.7)
        values = await testmodels.DecimalFields.get(id=obj0.id).values_list(
            "decimal", "decimal_nodec"
        )
        self.assertEqual(list(values[0]), [Decimal("1.2346"), 19])
