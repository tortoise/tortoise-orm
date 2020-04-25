from enum import IntEnum

from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.fields import CharEnumField, IntEnumField


class BadIntEnum1(IntEnum):
    python_programming = 32768
    database_design = 2
    system_administration = 3


class BadIntEnum2(IntEnum):
    python_programming = -1
    database_design = 2
    system_administration = 3


class TestIntEnumFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.EnumFields.create()

    async def test_create(self):
        obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
        self.assertIsInstance(obj0.service, testmodels.Service)
        obj = await testmodels.EnumFields.get(id=obj0.id)
        self.assertIsInstance(obj.service, testmodels.Service)
        self.assertEqual(obj.service, testmodels.Service.system_administration)
        await obj.save()
        obj2 = await testmodels.EnumFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

        await obj.delete()
        obj = await testmodels.EnumFields.filter(id=obj0.id).first()
        self.assertEqual(obj, None)

        obj3 = await testmodels.EnumFields.create(service=3)
        self.assertIsInstance(obj3.service, testmodels.Service)
        with self.assertRaises(ValueError):
            await testmodels.EnumFields.create(service=4)

    async def test_update(self):
        obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
        await testmodels.EnumFields.filter(id=obj0.id).update(
            service=testmodels.Service.database_design
        )
        obj = await testmodels.EnumFields.get(id=obj0.id)
        self.assertEqual(obj.service, testmodels.Service.database_design)

        await testmodels.EnumFields.filter(id=obj0.id).update(service=2)
        obj = await testmodels.EnumFields.get(id=obj0.id)
        self.assertEqual(obj.service, testmodels.Service.database_design)
        with self.assertRaises(ValueError):
            await testmodels.EnumFields.filter(id=obj0.id).update(service=4)

    async def test_values(self):
        obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
        values = await testmodels.EnumFields.get(id=obj0.id).values("service")
        self.assertEqual(values[0]["service"], testmodels.Service.system_administration)

        obj1 = await testmodels.EnumFields.create(service=3)
        values = await testmodels.EnumFields.get(id=obj1.id).values("service")
        self.assertEqual(values[0]["service"], testmodels.Service.system_administration)

    async def test_values_list(self):
        obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
        values = await testmodels.EnumFields.get(id=obj0.id).values_list("service", flat=True)
        self.assertEqual(values[0], testmodels.Service.system_administration)

        obj1 = await testmodels.EnumFields.create(service=3)
        values = await testmodels.EnumFields.get(id=obj1.id).values_list("service", flat=True)
        self.assertEqual(values[0], testmodels.Service.system_administration)

    def test_char_fails(self):
        with self.assertRaisesRegex(
            ConfigurationError, "IntEnumField only supports integer enums!"
        ):
            IntEnumField(testmodels.Currency)

    def test_range1_fails(self):
        with self.assertRaisesRegex(
            ConfigurationError, "The valid range of IntEnumField's values is 0..32767!"
        ):
            IntEnumField(BadIntEnum1)

    def test_range2_fails(self):
        with self.assertRaisesRegex(
            ConfigurationError, "The valid range of IntEnumField's values is 0..32767!"
        ):
            IntEnumField(BadIntEnum2)

    def test_auto_description(self):
        fld = IntEnumField(testmodels.Service)
        self.assertEqual(
            fld.description, "python_programming: 1\ndatabase_design: 2\nsystem_administration: 3"
        )

    def test_manual_description(self):
        fld = IntEnumField(testmodels.Service, description="foo")
        self.assertEqual(fld.description, "foo")


class TestCharEnumFields(test.TestCase):
    async def test_create(self):
        obj0 = await testmodels.EnumFields.create(service=testmodels.Service.system_administration)
        self.assertIsInstance(obj0.currency, testmodels.Currency)
        obj = await testmodels.EnumFields.get(id=obj0.id)
        self.assertIsInstance(obj.currency, testmodels.Currency)
        self.assertEqual(obj.currency, testmodels.Currency.HUF)
        await obj.save()
        obj2 = await testmodels.EnumFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

        await obj.delete()
        obj = await testmodels.EnumFields.filter(id=obj0.id).first()
        self.assertEqual(obj, None)

        obj0 = await testmodels.EnumFields.create(
            service=testmodels.Service.system_administration, currency="USD"
        )
        self.assertIsInstance(obj0.currency, testmodels.Currency)
        with self.assertRaises(ValueError):
            await testmodels.EnumFields.create(
                service=testmodels.Service.system_administration, currency="XXX"
            )

    async def test_update(self):
        obj0 = await testmodels.EnumFields.create(
            service=testmodels.Service.system_administration, currency=testmodels.Currency.HUF
        )
        await testmodels.EnumFields.filter(id=obj0.id).update(currency=testmodels.Currency.EUR)
        obj = await testmodels.EnumFields.get(id=obj0.id)
        self.assertEqual(obj.currency, testmodels.Currency.EUR)

        await testmodels.EnumFields.filter(id=obj0.id).update(currency="USD")
        obj = await testmodels.EnumFields.get(id=obj0.id)
        self.assertEqual(obj.currency, testmodels.Currency.USD)
        with self.assertRaises(ValueError):
            await testmodels.EnumFields.filter(id=obj0.id).update(currency="XXX")

    async def test_values(self):
        obj0 = await testmodels.EnumFields.create(
            service=testmodels.Service.system_administration, currency=testmodels.Currency.EUR
        )
        values = await testmodels.EnumFields.get(id=obj0.id).values("currency")
        self.assertEqual(values[0]["currency"], testmodels.Currency.EUR)

        obj1 = await testmodels.EnumFields.create(service=3, currency="EUR")
        values = await testmodels.EnumFields.get(id=obj1.id).values("currency")
        self.assertEqual(values[0]["currency"], testmodels.Currency.EUR)

    async def test_values_list(self):
        obj0 = await testmodels.EnumFields.create(
            service=testmodels.Service.system_administration, currency=testmodels.Currency.EUR
        )
        values = await testmodels.EnumFields.get(id=obj0.id).values_list("currency", flat=True)
        self.assertEqual(values[0], testmodels.Currency.EUR)

        obj1 = await testmodels.EnumFields.create(service=3, currency="EUR")
        values = await testmodels.EnumFields.get(id=obj1.id).values_list("currency", flat=True)
        self.assertEqual(values[0], testmodels.Currency.EUR)

    def test_auto_maxlen(self):
        fld = CharEnumField(testmodels.Currency)
        self.assertEqual(fld.max_length, 3)

    def test_defined_maxlen(self):
        fld = CharEnumField(testmodels.Currency, max_length=5)
        self.assertEqual(fld.max_length, 5)

    def test_auto_description(self):
        fld = CharEnumField(testmodels.Currency)
        self.assertEqual(fld.description, "HUF: HUF\nEUR: EUR\nUSD: USD")

    def test_manual_description(self):
        fld = CharEnumField(testmodels.Currency, description="baa")
        self.assertEqual(fld.description, "baa")
