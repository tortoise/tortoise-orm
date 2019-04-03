from tortoise.contrib import test
from tortoise.exceptions import IntegrityError
from tortoise.tests import testmodels


class TestJSONFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.JSONFields.create()

    async def test_create(self):
        obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})
        obj = await testmodels.JSONFields.get(id=obj0.id)
        self.assertEqual(obj.data, {"some": ["text", 3]})
        self.assertEqual(obj.data_null, None)
        await obj.save()
        obj2 = await testmodels.JSONFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_list(self):
        obj0 = await testmodels.JSONFields.create(data=["text", 3])
        obj = await testmodels.JSONFields.get(id=obj0.id)
        self.assertEqual(obj.data, ["text", 3])
        self.assertEqual(obj.data_null, None)
        await obj.save()
        obj2 = await testmodels.JSONFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})
        values = await testmodels.JSONFields.filter(id=obj0.id).values("data")
        self.assertEqual(values[0]["data"], {"some": ["text", 3]})

    async def test_values_list(self):
        obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})
        values = await testmodels.JSONFields.filter(id=obj0.id).values_list("data", flat=True)
        self.assertEqual(values[0], {"some": ["text", 3]})
