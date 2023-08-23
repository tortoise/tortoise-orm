import uuid

from tests import testmodels_mysql
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError


class TestMySQLUUIDFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels_mysql.UUIDFields.create()

    async def test_create(self):
        data = uuid.uuid4()
        obj0 = await testmodels_mysql.UUIDFields.create(data=data)
        self.assertIsInstance(obj0.data, bytes)
        self.assertIsInstance(obj0.data_auto, bytes)
        self.assertEqual(obj0.data_null, None)
        obj = await testmodels_mysql.UUIDFields.get(id=obj0.id)
        self.assertIsInstance(obj.data, uuid.UUID)
        self.assertIsInstance(obj.data_auto, uuid.UUID)
        self.assertEqual(obj.data, data)
        self.assertEqual(obj.data_null, None)
        await obj.save()
        obj2 = await testmodels_mysql.UUIDFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

        await obj.delete()
        obj = await testmodels_mysql.UUIDFields.filter(id=obj0.id).first()
        self.assertEqual(obj, None)

    async def test_update(self):
        data = uuid.uuid4()
        data2 = uuid.uuid4()
        obj0 = await testmodels_mysql.UUIDFields.create(data=data)
        await testmodels_mysql.UUIDFields.filter(id=obj0.id).update(data=data2)
        obj = await testmodels_mysql.UUIDFields.get(id=obj0.id)
        self.assertEqual(obj.data, data2)
        self.assertEqual(obj.data_null, None)

    async def test_create_not_null(self):
        data = uuid.uuid4()
        obj0 = await testmodels_mysql.UUIDFields.create(data=data, data_null=data)
        obj = await testmodels_mysql.UUIDFields.get(id=obj0.id)
        self.assertEqual(obj.data, data)
        self.assertEqual(obj.data_null, data)
