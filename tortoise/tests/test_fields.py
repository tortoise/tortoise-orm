from datetime import date, datetime, timedelta
from decimal import Decimal
from time import sleep

from tortoise import fields
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.tests import testmodels


class TestFieldErrors(test.SimpleTestCase):

    def test_char_field_empty(self):
        with self.assertRaises(ConfigurationError):
            fields.CharField()

    def test_char_field_zero(self):
        with self.assertRaises(ConfigurationError):
            fields.CharField(max_length=0)

    def test_decimal_field_empty(self):
        with self.assertRaises(ConfigurationError):
            fields.DecimalField()

    def test_decimal_field_neg_digits(self):
        with self.assertRaises(ConfigurationError):
            fields.DecimalField(max_digits=0, decimal_places=2)

    def test_decimal_field_neg_decimal(self):
        with self.assertRaises(ConfigurationError):
            fields.DecimalField(max_digits=2, decimal_places=-1)

    def test_datetime_field_auto_bad(self):
        with self.assertRaises(ConfigurationError):
            fields.DatetimeField(auto_now=True, auto_now_add=True)


class TestIntFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.IntFields.create()

    async def test_create(self):
        obj0 = await testmodels.IntFields.create(intnum=1)
        obj = await testmodels.IntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 1)
        self.assertEqual(obj.intnum_null, None)
        await obj.save()
        obj2 = await testmodels.IntFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast(self):
        obj0 = await testmodels.IntFields.create(intnum='3')
        obj = await testmodels.IntFields.get(id=obj0.id)
        self.assertEqual(obj.intnum, 3)

    async def test_values(self):
        obj0 = await testmodels.IntFields.create(intnum=1)
        values = await testmodels.IntFields.get(id=obj0.id).values('intnum')
        self.assertEqual(values[0]['intnum'], 1)

    async def test_values_list(self):
        obj0 = await testmodels.IntFields.create(intnum=1)
        values = await testmodels.IntFields.get(id=obj0.id).values_list('intnum', flat=True)
        self.assertEqual(values[0], 1)


class TestSmallIntFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.SmallIntFields.create()

    async def test_create(self):
        obj0 = await testmodels.SmallIntFields.create(smallintnum=2)
        obj = await testmodels.SmallIntFields.get(id=obj0.id)
        self.assertEqual(obj.smallintnum, 2)
        self.assertEqual(obj.smallintnum_null, None)
        await obj.save()
        obj2 = await testmodels.SmallIntFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.SmallIntFields.create(smallintnum=2)
        values = await testmodels.SmallIntFields.get(id=obj0.id).values('smallintnum')
        self.assertEqual(values[0]['smallintnum'], 2)

    async def test_values_list(self):
        obj0 = await testmodels.SmallIntFields.create(smallintnum=2)
        values = await testmodels.SmallIntFields.get(
            id=obj0.id).values_list('smallintnum', flat=True)
        self.assertEqual(values[0], 2)


class TestCharFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.CharFields.create()

    async def test_create(self):
        obj0 = await testmodels.CharFields.create(char='moo')
        obj = await testmodels.CharFields.get(id=obj0.id)
        self.assertEqual(obj.char, 'moo')
        self.assertEqual(obj.char_null, None)
        await obj.save()
        obj2 = await testmodels.CharFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast(self):
        obj0 = await testmodels.CharFields.create(char=33)
        obj = await testmodels.CharFields.get(id=obj0.id)
        self.assertEqual(obj.char, '33')

    async def test_values(self):
        obj0 = await testmodels.CharFields.create(char='moo')
        values = await testmodels.CharFields.get(id=obj0.id).values('char')
        self.assertEqual(values[0]['char'], 'moo')

    async def test_values_list(self):
        obj0 = await testmodels.CharFields.create(char='moo')
        values = await testmodels.CharFields.get(id=obj0.id).values_list('char', flat=True)
        self.assertEqual(values[0], 'moo')


class TestTextFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.TextFields.create()

    async def test_create(self):
        obj0 = await testmodels.TextFields.create(text='baa')
        obj = await testmodels.TextFields.get(id=obj0.id)
        self.assertEqual(obj.text, 'baa')
        self.assertEqual(obj.text_null, None)
        await obj.save()
        obj2 = await testmodels.TextFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.TextFields.create(text='baa')
        values = await testmodels.TextFields.get(id=obj0.id).values('text')
        self.assertEqual(values[0]['text'], 'baa')

    async def test_values_list(self):
        obj0 = await testmodels.TextFields.create(text='baa')
        values = await testmodels.TextFields.get(id=obj0.id).values_list('text', flat=True)
        self.assertEqual(values[0], 'baa')


class TestBooleanFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.BooleanFields.create()

    async def test_create(self):
        obj0 = await testmodels.BooleanFields.create(boolean=True)
        obj = await testmodels.BooleanFields.get(id=obj0.id)
        self.assertEqual(obj.boolean, True)
        self.assertEqual(obj.boolean_null, None)
        await obj.save()
        obj2 = await testmodels.BooleanFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.BooleanFields.create(boolean=True)
        values = await testmodels.BooleanFields.get(id=obj0.id).values('boolean')
        self.assertEqual(values[0]['boolean'], True)

    async def test_values_list(self):
        obj0 = await testmodels.BooleanFields.create(boolean=True)
        values = await testmodels.BooleanFields.get(id=obj0.id).values_list('boolean', flat=True)
        self.assertEqual(values[0], True)


class TestDecimalFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.DecimalFields.create()

    async def test_create(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal('1.23456'), decimal_nodec=18.7)
        obj = await testmodels.DecimalFields.get(id=obj0.id)
        self.assertEqual(obj.decimal, Decimal('1.2346'))
        self.assertEqual(obj.decimal_nodec, 19)
        self.assertEqual(obj.decimal_null, None)
        await obj.save()
        obj2 = await testmodels.DecimalFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal('1.23456'), decimal_nodec=18.7)
        values = await testmodels.DecimalFields.get(id=obj0.id).values('decimal', 'decimal_nodec')
        self.assertEqual(values[0]['decimal'], Decimal('1.2346'))
        self.assertEqual(values[0]['decimal_nodec'], 19)

    async def test_values_list(self):
        obj0 = await testmodels.DecimalFields.create(decimal=Decimal('1.23456'), decimal_nodec=18.7)
        values = await testmodels.DecimalFields.get(
            id=obj0.id).values_list('decimal', 'decimal_nodec')
        self.assertEqual(list(values[0]), [Decimal('1.2346'), 19])


class TestDatetimeFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.DatetimeFields.create()

    async def test_create(self):
        now = datetime.utcnow()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        obj = await testmodels.DatetimeFields.get(id=obj0.id)
        self.assertEqual(obj.datetime, now)
        self.assertEqual(obj.datetime_null, None)
        self.assertLess(obj.datetime_auto - now, timedelta(seconds=1))
        self.assertLess(obj.datetime_add - now, timedelta(seconds=1))
        datetime_auto = obj.datetime_auto
        sleep(1)
        await obj.save()
        obj2 = await testmodels.DatetimeFields.get(id=obj.id)
        self.assertEqual(obj2.datetime, now)
        self.assertEqual(obj2.datetime_null, None)
        self.assertEqual(obj2.datetime_auto, obj.datetime_auto)
        self.assertNotEqual(obj2.datetime_auto, datetime_auto)
        self.assertGreater(obj2.datetime_auto - now, timedelta(seconds=1))
        self.assertLess(obj2.datetime_auto - now, timedelta(seconds=2))
        self.assertEqual(obj2.datetime_add, obj.datetime_add)

    async def test_cast(self):
        now = datetime.utcnow()
        obj0 = await testmodels.DatetimeFields.create(datetime=now.isoformat())
        obj = await testmodels.DatetimeFields.get(id=obj0.id)
        self.assertEqual(obj.datetime, now)

    async def test_values(self):
        now = datetime.utcnow()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        values = await testmodels.DatetimeFields.get(id=obj0.id).values('datetime')
        self.assertEqual(values[0]['datetime'], now)

    async def test_values_list(self):
        now = datetime.utcnow()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        values = await testmodels.DatetimeFields.get(id=obj0.id).values_list('datetime', flat=True)
        self.assertEqual(values[0], now)


class TestDateFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.DateFields.create()

    async def test_create(self):
        today = date.today()
        obj0 = await testmodels.DateFields.create(date=today)
        obj = await testmodels.DateFields.get(id=obj0.id)
        self.assertEqual(obj.date, today)
        self.assertEqual(obj.date_null, None)
        await obj.save()
        obj2 = await testmodels.DateFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast(self):
        today = date.today()
        obj0 = await testmodels.DateFields.create(date=today.isoformat())
        obj = await testmodels.DateFields.get(id=obj0.id)
        self.assertEqual(obj.date, today)

    async def test_values(self):
        today = date.today()
        obj0 = await testmodels.DateFields.create(date=today)
        values = await testmodels.DateFields.get(id=obj0.id).values('date')
        self.assertEqual(values[0]['date'], today)

    async def test_values_list(self):
        today = date.today()
        obj0 = await testmodels.DateFields.create(date=today)
        values = await testmodels.DateFields.get(id=obj0.id).values_list('date', flat=True)
        self.assertEqual(values[0], today)


class TestFloatFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.FloatFields.create()

    async def test_create(self):
        obj0 = await testmodels.FloatFields.create(floatnum=1.23)
        obj = await testmodels.FloatFields.get(id=obj0.id)
        self.assertEqual(obj.floatnum, 1.23)
        self.assertNotEqual(Decimal(obj.floatnum), Decimal('1.23'))
        self.assertEqual(obj.floatnum_null, None)
        await obj.save()
        obj2 = await testmodels.FloatFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast_int(self):
        obj0 = await testmodels.FloatFields.create(floatnum=123)
        obj = await testmodels.FloatFields.get(id=obj0.id)
        self.assertEqual(obj.floatnum, 123)

    async def test_cast_decimal(self):
        obj0 = await testmodels.FloatFields.create(floatnum=Decimal('1.23'))
        obj = await testmodels.FloatFields.get(id=obj0.id)
        self.assertEqual(obj.floatnum, 1.23)

    async def test_values(self):
        obj0 = await testmodels.FloatFields.create(floatnum=1.23)
        values = await testmodels.FloatFields.filter(id=obj0.id).values('floatnum')
        self.assertEqual(values[0]['floatnum'], 1.23)

    async def test_values_list(self):
        obj0 = await testmodels.FloatFields.create(floatnum=1.23)
        values = await testmodels.FloatFields.filter(id=obj0.id).values_list('floatnum')
        self.assertEqual(list(values[0]), [1.23])


class TestJSONFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.JSONFields.create()

    async def test_create(self):
        obj0 = await testmodels.JSONFields.create(data={'some': ['text', 3]})
        obj = await testmodels.JSONFields.get(id=obj0.id)
        self.assertEqual(obj.data, {'some': ['text', 3]})
        self.assertEqual(obj.data_null, None)
        await obj.save()
        obj2 = await testmodels.JSONFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_list(self):
        obj0 = await testmodels.JSONFields.create(data=['text', 3])
        obj = await testmodels.JSONFields.get(id=obj0.id)
        self.assertEqual(obj.data, ['text', 3])
        self.assertEqual(obj.data_null, None)
        await obj.save()
        obj2 = await testmodels.JSONFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.JSONFields.create(data={'some': ['text', 3]})
        values = await testmodels.JSONFields.filter(id=obj0.id).values('data')
        self.assertEqual(values[0]['data'], {'some': ['text', 3]})

    async def test_values_list(self):
        obj0 = await testmodels.JSONFields.create(data={'some': ['text', 3]})
        values = await testmodels.JSONFields.filter(id=obj0.id).values_list('data', flat=True)
        self.assertEqual(values[0], {'some': ['text', 3]})
