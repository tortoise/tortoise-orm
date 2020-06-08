from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, FieldError, IntegrityError
from tortoise.fields import JSONField


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

    async def test_error(self):
        with self.assertRaises(FieldError):
            await testmodels.JSONFields.create(data='{"some": ')

        obj = await testmodels.JSONFields.create(data='{"some": ["text", 3]}')
        with self.assertRaises(FieldError):
            await testmodels.JSONFields.filter(pk=obj.pk).update(data='{"some": ')

        with self.assertRaises(FieldError):
            obj.data = "error json"
            await obj.save()

    async def test_update(self):
        obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})
        await testmodels.JSONFields.filter(id=obj0.id).update(data={"other": ["text", 5]})
        obj = await testmodels.JSONFields.get(id=obj0.id)
        self.assertEqual(obj.data, {"other": ["text", 5]})
        self.assertEqual(obj.data_null, None)

    async def test_dict_str(self):
        obj0 = await testmodels.JSONFields.create(data={"some": ["text", 3]})

        obj = await testmodels.JSONFields.get(id=obj0.id)
        self.assertEqual(obj.data, {"some": ["text", 3]})

        await testmodels.JSONFields.filter(id=obj0.id).update(data='{"other": ["text", 5]}')
        obj = await testmodels.JSONFields.get(id=obj0.id)
        self.assertEqual(obj.data, {"other": ["text", 5]})

    async def test_list_str(self):
        obj = await testmodels.JSONFields.create(data='["text", 3]')
        obj0 = await testmodels.JSONFields.get(id=obj.id)
        self.assertEqual(obj0.data, ["text", 3])

        await testmodels.JSONFields.filter(id=obj.id).update(data='["text", 5]')
        obj0 = await testmodels.JSONFields.get(id=obj.id)
        self.assertEqual(obj0.data, ["text", 5])

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

    def test_unique_fail(self):
        with self.assertRaisesRegex(ConfigurationError, "can't be indexed"):
            JSONField(unique=True)

    def test_index_fail(self):
        with self.assertRaisesRegex(ConfigurationError, "can't be indexed"):
            JSONField(index=True)
