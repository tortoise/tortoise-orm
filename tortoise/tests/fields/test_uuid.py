import uuid

from tortoise.contrib import test
from tortoise.exceptions import IntegrityError
from tortoise.tests import testmodels


class TestUUIDFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.UUIDFields.create()

    async def test_create(self):
        data = uuid.uuid4()
        obj0 = await testmodels.UUIDFields.create(data=data)
        obj = await testmodels.UUIDFields.get(id=obj0.id)
        self.assertEqual(obj.data, data)
        self.assertEqual(obj.data_null, None)
        await obj.save()
        obj2 = await testmodels.UUIDFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_create_not_null(self):
        data = uuid.uuid4()
        obj0 = await testmodels.UUIDFields.create(data=data, data_null=data)
        obj = await testmodels.UUIDFields.get(id=obj0.id)
        self.assertEqual(obj.data, data)
        self.assertEqual(obj.data_null, data)
