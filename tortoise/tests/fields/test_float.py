from decimal import Decimal

from tortoise.contrib import test
from tortoise.exceptions import IntegrityError
from tortoise.tests import testmodels


class TestFloatFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.FloatFields.create()

    async def test_create(self):
        obj0 = await testmodels.FloatFields.create(floatnum=1.23)
        obj = await testmodels.FloatFields.get(id=obj0.id)
        self.assertEqual(obj.floatnum, 1.23)
        self.assertNotEqual(Decimal(obj.floatnum), Decimal("1.23"))
        self.assertEqual(obj.floatnum_null, None)
        await obj.save()
        obj2 = await testmodels.FloatFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast_int(self):
        obj0 = await testmodels.FloatFields.create(floatnum=123)
        obj = await testmodels.FloatFields.get(id=obj0.id)
        self.assertEqual(obj.floatnum, 123)

    async def test_cast_decimal(self):
        obj0 = await testmodels.FloatFields.create(floatnum=Decimal("1.23"))
        obj = await testmodels.FloatFields.get(id=obj0.id)
        self.assertEqual(obj.floatnum, 1.23)

    async def test_values(self):
        obj0 = await testmodels.FloatFields.create(floatnum=1.23)
        values = await testmodels.FloatFields.filter(id=obj0.id).values("floatnum")
        self.assertEqual(values[0]["floatnum"], 1.23)

    async def test_values_list(self):
        obj0 = await testmodels.FloatFields.create(floatnum=1.23)
        values = await testmodels.FloatFields.filter(id=obj0.id).values_list("floatnum")
        self.assertEqual(list(values[0]), [1.23])
