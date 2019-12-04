from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError


class TestEnumFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.EnumFields.create()

    async def test_create(self):
        obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
        self.assertIsInstance(obj0.service, testmodels.Service)
        self.assertIsInstance(obj0.currency, testmodels.Currency)
        obj = await testmodels.EnumFields.get(id=obj0.id)
        self.assertIsInstance(obj.service, testmodels.Service)
        self.assertIsInstance(obj.currency, testmodels.Currency)
        self.assertEqual(obj.service, testmodels.Service.system_administration)
        self.assertEqual(obj.currency, testmodels.Currency.HUF)
        await obj.save()
        obj2 = await testmodels.EnumFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

        await obj.delete()
        obj = await testmodels.EnumFields.filter(id=obj0.id).first()
        self.assertEqual(obj, None)

    async def test_update(self):
        obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
        await testmodels.EnumFields.filter(id=obj0.id).update(
            service=testmodels.Service.database_design, currency=testmodels.Currency.EUR
        )
        obj = await testmodels.EnumFields.get(id=obj0.id)
        self.assertEqual(obj.service, testmodels.Service.database_design)
        self.assertEqual(obj.currency, testmodels.Currency.EUR)
