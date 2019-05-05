from datetime import date, datetime, timedelta
from time import sleep

from tortoise import fields
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.tests import testmodels


class TestDatetimeFields(test.TestCase):
    def test_both_auto_bad(self):
        with self.assertRaisesRegex(
            ConfigurationError, "You can choose only 'auto_now' or 'auto_now_add'"
        ):
            fields.DatetimeField(auto_now=True, auto_now_add=True)

    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.DatetimeFields.create()

    async def test_create(self):
        now = datetime.utcnow()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        obj = await testmodels.DatetimeFields.get(id=obj0.id)
        self.assertEqual(obj.datetime, now)
        self.assertEqual(obj.datetime_null, None)
        self.assertLess(obj.datetime_auto - now, timedelta(microseconds=10000))
        self.assertLess(obj.datetime_add - now, timedelta(microseconds=10000))
        datetime_auto = obj.datetime_auto
        sleep(0.011)
        await obj.save()
        obj2 = await testmodels.DatetimeFields.get(id=obj.id)
        self.assertEqual(obj2.datetime, now)
        self.assertEqual(obj2.datetime_null, None)
        self.assertEqual(obj2.datetime_auto, obj.datetime_auto)
        self.assertNotEqual(obj2.datetime_auto, datetime_auto)
        self.assertGreater(obj2.datetime_auto - now, timedelta(microseconds=10000))
        self.assertLess(obj2.datetime_auto - now, timedelta(seconds=1))
        self.assertEqual(obj2.datetime_add, obj.datetime_add)

    async def test_cast(self):
        now = datetime.utcnow()
        obj0 = await testmodels.DatetimeFields.create(datetime=now.isoformat())
        obj = await testmodels.DatetimeFields.get(id=obj0.id)
        self.assertEqual(obj.datetime, now)

    async def test_values(self):
        now = datetime.utcnow()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        values = await testmodels.DatetimeFields.get(id=obj0.id).values("datetime")
        self.assertEqual(values[0]["datetime"], now)

    async def test_values_list(self):
        now = datetime.utcnow()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        values = await testmodels.DatetimeFields.get(id=obj0.id).values_list("datetime", flat=True)
        self.assertEqual(values[0], now)

    async def test_get_utcnow(self):
        now = datetime.utcnow()
        await testmodels.DatetimeFields.create(datetime=now)
        obj = await testmodels.DatetimeFields.get(datetime=now)
        self.assertEqual(obj.datetime, now)

    async def test_get_now(self):
        now = datetime.now()
        await testmodels.DatetimeFields.create(datetime=now)
        obj = await testmodels.DatetimeFields.get(datetime=now)
        self.assertEqual(obj.datetime, now)


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
        values = await testmodels.DateFields.get(id=obj0.id).values("date")
        self.assertEqual(values[0]["date"], today)

    async def test_values_list(self):
        today = date.today()
        obj0 = await testmodels.DateFields.create(date=today)
        values = await testmodels.DateFields.get(id=obj0.id).values_list("date", flat=True)
        self.assertEqual(values[0], today)

    async def test_get(self):
        today = date.today()
        await testmodels.DateFields.create(date=today)
        obj = await testmodels.DateFields.get(date=today)
        self.assertEqual(obj.date, today)


class TestTimeDeltaFields(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.TimeDeltaFields.create()

    async def test_create(self):
        obj0 = await testmodels.TimeDeltaFields.create(
            timedelta=timedelta(days=35, seconds=8, microseconds=1)
        )
        obj = await testmodels.TimeDeltaFields.get(id=obj0.id)
        self.assertEqual(obj.timedelta, timedelta(days=35, seconds=8, microseconds=1))
        self.assertEqual(obj.timedelta_null, None)
        await obj.save()
        obj2 = await testmodels.TimeDeltaFields.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await testmodels.TimeDeltaFields.create(
            timedelta=timedelta(days=35, seconds=8, microseconds=1)
        )
        values = await testmodels.TimeDeltaFields.get(id=obj0.id).values("timedelta")
        self.assertEqual(values[0]["timedelta"], timedelta(days=35, seconds=8, microseconds=1))

    async def test_values_list(self):
        obj0 = await testmodels.TimeDeltaFields.create(
            timedelta=timedelta(days=35, seconds=8, microseconds=1)
        )
        values = await testmodels.TimeDeltaFields.get(id=obj0.id).values_list(
            "timedelta", flat=True
        )
        self.assertEqual(values[0], timedelta(days=35, seconds=8, microseconds=1))

    async def test_get(self):
        delta = timedelta(days=35, seconds=8, microseconds=1)
        await testmodels.TimeDeltaFields.create(timedelta=delta)
        obj = await testmodels.TimeDeltaFields.get(timedelta=delta)
        self.assertEqual(obj.timedelta, delta)
