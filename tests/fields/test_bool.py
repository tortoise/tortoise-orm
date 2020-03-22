from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError


class TestBooleanFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.BooleanFields.create()

    async def test_create(self):
        obj0 = await testmodels.BooleanFields.create(boolean=True)
        obj = await testmodels.BooleanFields.get(id=obj0.id)
        self.assertIs(obj.boolean, True)
        self.assertIs(obj.boolean_null, None)
        await obj.save()
        obj2 = await testmodels.BooleanFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_update(self):
        obj0 = await testmodels.BooleanFields.create(boolean=False)
        await testmodels.BooleanFields.filter(id=obj0.id).update(boolean=False)
        obj = await testmodels.BooleanFields.get(id=obj0.id)
        self.assertIs(obj.boolean, False)
        self.assertIs(obj.boolean_null, None)

    async def test_values(self):
        obj0 = await testmodels.BooleanFields.create(boolean=True)
        values = await testmodels.BooleanFields.get(id=obj0.id).values("boolean")
        self.assertIs(values[0]["boolean"], True)

    async def test_values_list(self):
        obj0 = await testmodels.BooleanFields.create(boolean=True)
        values = await testmodels.BooleanFields.get(id=obj0.id).values_list("boolean", flat=True)
        self.assertIs(values[0], True)
