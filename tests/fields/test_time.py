import os
from datetime import date, datetime, timedelta
from time import sleep

import pytz
from iso8601 import ParseError

from tests import testmodels
from tortoise import fields, timezone
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.timezone import get_default_timezone


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
        now = timezone.now()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        obj = await testmodels.DatetimeFields.get(id=obj0.id)
        self.assertEqual(obj.datetime, now)
        self.assertEqual(obj.datetime_null, None)
        self.assertLess(obj.datetime_auto - now, timedelta(microseconds=20000))
        self.assertLess(obj.datetime_add - now, timedelta(microseconds=20000))
        datetime_auto = obj.datetime_auto
        sleep(0.012)
        await obj.save()
        obj2 = await testmodels.DatetimeFields.get(id=obj.id)
        self.assertEqual(obj2.datetime, now)
        self.assertEqual(obj2.datetime_null, None)
        self.assertEqual(obj2.datetime_auto, obj.datetime_auto)
        self.assertNotEqual(obj2.datetime_auto, datetime_auto)
        self.assertGreater(obj2.datetime_auto - now, timedelta(microseconds=10000))
        self.assertLess(obj2.datetime_auto - now, timedelta(seconds=1))
        self.assertEqual(obj2.datetime_add, obj.datetime_add)

    async def test_update(self):
        obj0 = await testmodels.DatetimeFields.create(datetime=datetime(2019, 9, 1, 0, 0, 0))
        await testmodels.DatetimeFields.filter(id=obj0.id).update(
            datetime=datetime(2019, 9, 1, 6, 0, 8)
        )
        obj = await testmodels.DatetimeFields.get(id=obj0.id)
        self.assertEqual(obj.datetime, datetime(2019, 9, 1, 6, 0, 8, tzinfo=get_default_timezone()))
        self.assertEqual(obj.datetime_null, None)

    async def test_cast(self):
        now = timezone.now()
        obj0 = await testmodels.DatetimeFields.create(datetime=now.isoformat())
        obj = await testmodels.DatetimeFields.get(id=obj0.id)
        self.assertEqual(obj.datetime, now)

    async def test_values(self):
        now = timezone.now()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        values = await testmodels.DatetimeFields.get(id=obj0.id).values("datetime")
        self.assertEqual(values[0]["datetime"], now)

    async def test_values_list(self):
        now = timezone.now()
        obj0 = await testmodels.DatetimeFields.create(datetime=now)
        values = await testmodels.DatetimeFields.get(id=obj0.id).values_list("datetime", flat=True)
        self.assertEqual(values[0], now)

    async def test_get_utcnow(self):
        now = datetime.utcnow().replace(tzinfo=get_default_timezone())
        await testmodels.DatetimeFields.create(datetime=now)
        obj = await testmodels.DatetimeFields.get(datetime=now)
        self.assertEqual(obj.datetime, now)

    async def test_get_now(self):
        now = timezone.now()
        await testmodels.DatetimeFields.create(datetime=now)
        obj = await testmodels.DatetimeFields.get(datetime=now)
        self.assertEqual(obj.datetime, now)

    async def test_count(self):
        now = timezone.now()
        obj = await testmodels.DatetimeFields.create(datetime=now)
        self.assertEqual(await testmodels.DatetimeFields.filter(datetime=obj.datetime).count(), 1)
        self.assertEqual(
            await testmodels.DatetimeFields.filter(datetime_auto=obj.datetime_auto).count(), 1
        )
        self.assertEqual(
            await testmodels.DatetimeFields.filter(datetime_add=obj.datetime_add).count(), 1
        )

    async def test_date_str(self):
        obj0 = await testmodels.DateFields.create(date="2020-08-17")
        obj1 = await testmodels.DateFields.get(date="2020-08-17")
        self.assertEqual(obj0.date, obj1.date)
        with self.assertRaises(
            (ParseError, ValueError),
        ):
            await testmodels.DateFields.create(date="2020-08-xx")
        await testmodels.DateFields.filter(date="2020-08-17").update(date="2020-08-18")
        obj2 = await testmodels.DateFields.get(date="2020-08-18")
        self.assertEqual(obj2.date, date(year=2020, month=8, day=18))

    async def test_default_timezone(self):
        now = timezone.now()
        obj = await testmodels.DatetimeFields.create(datetime=now)
        self.assertEqual(obj.datetime.tzinfo.zone, "UTC")

        obj_get = await testmodels.DatetimeFields.get(pk=obj.pk)
        self.assertEqual(obj_get.datetime.tzinfo.zone, "UTC")
        self.assertEqual(obj_get.datetime, now)

    async def test_set_timezone(self):
        old_tz = os.environ["TZ"]
        tz = "Asia/Shanghai"
        os.environ["TZ"] = tz
        now = datetime.now(pytz.timezone(tz))
        obj = await testmodels.DatetimeFields.create(datetime=now)
        self.assertEqual(obj.datetime.tzinfo.zone, tz)

        obj_get = await testmodels.DatetimeFields.get(pk=obj.pk)
        self.assertEqual(obj_get.datetime.tzinfo.zone, tz)
        self.assertEqual(obj_get.datetime, now)

        os.environ["TZ"] = old_tz

    async def test_timezone(self):
        old_tz = os.environ["TZ"]
        old_use_tz = os.environ["USE_TZ"]
        tz = "Asia/Shanghai"
        os.environ["TZ"] = tz
        os.environ["USE_TZ"] = "True"

        now = datetime.now(pytz.timezone(tz))
        obj = await testmodels.DatetimeFields.create(datetime=now)
        self.assertEqual(obj.datetime.tzinfo.zone, tz)
        obj_get = await testmodels.DatetimeFields.get(pk=obj.pk)
        self.assertEqual(obj.datetime.tzinfo.zone, tz)
        self.assertEqual(obj_get.datetime, now)

        os.environ["TZ"] = old_tz
        os.environ["USE_TZ"] = old_use_tz


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

    async def test_date_str(self):
        obj0 = await testmodels.DateFields.create(date="2020-08-17")
        obj1 = await testmodels.DateFields.get(date="2020-08-17")
        self.assertEqual(obj0.date, obj1.date)
        with self.assertRaises(Exception):
            await testmodels.DateFields.create(date="2020-08-xx")
        await testmodels.DateFields.filter(date="2020-08-17").update(date="2020-08-18")
        obj2 = await testmodels.DateFields.get(date="2020-08-18")
        self.assertEqual(obj2.date, date(year=2020, month=8, day=18))


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
