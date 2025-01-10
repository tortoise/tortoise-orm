import os
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from time import sleep
from typing import Type
from unittest.mock import patch

import pytz
from iso8601 import ParseError

from tests import testmodels
from tortoise import Model, fields, timezone
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotIn
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.expressions import F
from tortoise.timezone import get_default_timezone


class TestEmpty(test.TestCase):
    model: Type[Model] = testmodels.DatetimeFields

    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await self.model.create()


class TestDatetimeFields(TestEmpty):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        timezone._reset_timezone_cache()

    async def asyncTearDown(self):
        await super().asyncTearDown()
        timezone._reset_timezone_cache()

    def test_both_auto_bad(self):
        with self.assertRaisesRegex(
            ConfigurationError, "You can choose only 'auto_now' or 'auto_now_add'"
        ):
            fields.DatetimeField(auto_now=True, auto_now_add=True)

    async def test_create(self):
        now = timezone.now()
        obj0 = await self.model.create(datetime=now)
        obj = await self.model.get(id=obj0.id)
        self.assertEqual(obj.datetime, now)
        self.assertEqual(obj.datetime_null, None)
        self.assertLess(obj.datetime_auto - now, timedelta(microseconds=20000))
        self.assertLess(obj.datetime_add - now, timedelta(microseconds=20000))
        datetime_auto = obj.datetime_auto
        sleep(0.012)
        await obj.save()
        obj2 = await self.model.get(id=obj.id)
        self.assertEqual(obj2.datetime, now)
        self.assertEqual(obj2.datetime_null, None)
        self.assertEqual(obj2.datetime_auto, obj.datetime_auto)
        self.assertNotEqual(obj2.datetime_auto, datetime_auto)
        self.assertGreater(obj2.datetime_auto - now, timedelta(microseconds=10000))
        self.assertLess(obj2.datetime_auto - now, timedelta(seconds=1))
        self.assertEqual(obj2.datetime_add, obj.datetime_add)

    async def test_update(self):
        obj0 = await self.model.create(
            datetime=datetime(2019, 9, 1, 0, 0, 0, tzinfo=get_default_timezone())
        )
        await self.model.filter(id=obj0.id).update(
            datetime=datetime(2019, 9, 1, 6, 0, 8, tzinfo=get_default_timezone())
        )
        obj = await self.model.get(id=obj0.id)
        self.assertEqual(obj.datetime, datetime(2019, 9, 1, 6, 0, 8, tzinfo=get_default_timezone()))
        self.assertEqual(obj.datetime_null, None)

    async def test_filter(self):
        now = timezone.now()
        obj = await self.model.create(datetime=now)
        self.assertEqual(await self.model.filter(datetime=now).first(), obj)
        self.assertEqual(await self.model.annotate(d=F("datetime")).filter(d=now).first(), obj)

    async def test_cast(self):
        now = timezone.now()
        obj0 = await self.model.create(datetime=now.isoformat())
        obj = await self.model.get(id=obj0.id)
        self.assertEqual(obj.datetime, now)

    async def test_values(self):
        now = timezone.now()
        obj0 = await self.model.create(datetime=now)
        values = await self.model.get(id=obj0.id).values("datetime")
        self.assertEqual(values["datetime"], now)

    async def test_values_list(self):
        now = timezone.now()
        obj0 = await self.model.create(datetime=now)
        values = await self.model.get(id=obj0.id).values_list("datetime", flat=True)
        self.assertEqual(values, now)

    async def test_get_utcnow(self):
        now = datetime.now(dt_timezone.utc).replace(tzinfo=get_default_timezone())
        await self.model.create(datetime=now)
        obj = await self.model.get(datetime=now)
        self.assertEqual(obj.datetime, now)

    async def test_get_now(self):
        now = timezone.now()
        await self.model.create(datetime=now)
        obj = await self.model.get(datetime=now)
        self.assertEqual(obj.datetime, now)

    async def test_count(self):
        now = timezone.now()
        obj = await self.model.create(datetime=now)
        self.assertEqual(await self.model.filter(datetime=obj.datetime).count(), 1)
        self.assertEqual(await self.model.filter(datetime_auto=obj.datetime_auto).count(), 1)
        self.assertEqual(await self.model.filter(datetime_add=obj.datetime_add).count(), 1)

    async def test_default_timezone(self):
        now = timezone.now()
        obj = await self.model.create(datetime=now)
        self.assertEqual(obj.datetime.tzinfo.zone, "UTC")

        obj_get = await self.model.get(pk=obj.pk)
        self.assertEqual(obj_get.datetime.tzinfo.zone, "UTC")
        self.assertEqual(obj_get.datetime, now)

    async def test_set_timezone(self):
        old_tz = os.environ["TIMEZONE"]
        tz = "Asia/Shanghai"
        os.environ["TIMEZONE"] = tz
        now = datetime.now(pytz.timezone(tz))
        obj = await self.model.create(datetime=now)
        self.assertEqual(obj.datetime.tzinfo.zone, tz)

        obj_get = await self.model.get(pk=obj.pk)
        self.assertEqual(obj_get.datetime.tzinfo.zone, tz)
        self.assertEqual(obj_get.datetime, now)

        os.environ["TIMEZONE"] = old_tz

    async def test_timezone(self):
        old_tz = os.environ["TIMEZONE"]
        old_use_tz = os.environ["USE_TZ"]
        tz = "Asia/Shanghai"
        os.environ["TIMEZONE"] = tz
        os.environ["USE_TZ"] = "True"

        now = datetime.now(pytz.timezone(tz))
        obj = await self.model.create(datetime=now)
        self.assertEqual(obj.datetime.tzinfo.zone, tz)
        obj_get = await self.model.get(pk=obj.pk)
        self.assertEqual(obj.datetime.tzinfo.zone, tz)
        self.assertEqual(obj_get.datetime, now)

        os.environ["TIMEZONE"] = old_tz
        os.environ["USE_TZ"] = old_use_tz

    @test.requireCapability(dialect=NotIn("sqlite", "mssql"))
    async def test_filter_by_year_month_day(self):
        with patch.dict(os.environ, {"USE_TZ": "True"}):
            obj = await self.model.create(datetime=datetime(2024, 1, 2))
            same_year_objs = await self.model.filter(datetime__year=2024)
            filtered_obj = await self.model.filter(
                datetime__year=2024, datetime__month=1, datetime__day=2
            ).first()
            assert obj == filtered_obj
            assert obj.id in [i.id for i in same_year_objs]


class TestTime(test.TestCase):
    model = testmodels.TimeFields


@test.requireCapability(dialect="sqlite")
@test.requireCapability(dialect="postgres")
class TestTimeFields(TestTime):
    async def test_create(self):
        now = timezone.now().timetz()
        obj0 = await self.model.create(time=now)
        boj1 = await self.model.get(id=obj0.id)
        self.assertEqual(boj1.time, now)

    async def test_cast(self):
        obj0 = await self.model.create(time="21:00+00:00")
        obj1 = await self.model.get(id=obj0.id)
        self.assertEqual(obj1.time, time.fromisoformat("21:00+00:00"))

    async def test_values(self):
        now = timezone.now().timetz()
        obj0 = await self.model.create(time=now)
        values = await self.model.get(id=obj0.id).values("time")
        self.assertEqual(values["time"], now)

    async def test_values_list(self):
        now = timezone.now().timetz()
        obj0 = await self.model.create(time=now)
        values = await self.model.get(id=obj0.id).values_list("time", flat=True)
        self.assertEqual(values, now)

    async def test_get(self):
        now = timezone.now().timetz()
        await self.model.create(time=now)
        obj = await self.model.get(time=now)
        self.assertEqual(obj.time, now)


@test.requireCapability(dialect="mysql")
class TestTimeFieldsMySQL(TestTime):
    async def test_create(self):
        now = timezone.now().timetz()
        obj0 = await self.model.create(time=now)
        boj1 = await self.model.get(id=obj0.id)
        self.assertEqual(
            boj1.time,
            timedelta(
                hours=now.hour,
                minutes=now.minute,
                seconds=now.second,
                microseconds=now.microsecond,
            ),
        )

    async def test_cast(self):
        obj0 = await self.model.create(time="21:00+00:00")
        obj1 = await self.model.get(id=obj0.id)
        t = time.fromisoformat("21:00+00:00")
        self.assertEqual(
            obj1.time,
            timedelta(
                hours=t.hour,
                minutes=t.minute,
                seconds=t.second,
                microseconds=t.microsecond,
            ),
        )

    async def test_values(self):
        now = timezone.now().timetz()
        obj0 = await self.model.create(time=now)
        values = await self.model.get(id=obj0.id).values("time")
        self.assertEqual(
            values["time"],
            timedelta(
                hours=now.hour,
                minutes=now.minute,
                seconds=now.second,
                microseconds=now.microsecond,
            ),
        )

    async def test_values_list(self):
        now = timezone.now().timetz()
        obj0 = await self.model.create(time=now)
        values = await self.model.get(id=obj0.id).values_list("time", flat=True)
        self.assertEqual(
            values,
            timedelta(
                hours=now.hour,
                minutes=now.minute,
                seconds=now.second,
                microseconds=now.microsecond,
            ),
        )

    async def test_get(self):
        now = timezone.now().timetz()
        await self.model.create(time=now)
        obj = await self.model.get(time=now)
        self.assertEqual(
            obj.time,
            timedelta(
                hours=now.hour,
                minutes=now.minute,
                seconds=now.second,
                microseconds=now.microsecond,
            ),
        )


class TestDateFields(TestEmpty):
    model = testmodels.DateFields

    async def test_create(self):
        today = date.today()
        obj0 = await self.model.create(date=today)
        obj = await self.model.get(id=obj0.id)
        self.assertEqual(obj.date, today)
        self.assertEqual(obj.date_null, None)
        await obj.save()
        obj2 = await self.model.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_cast(self):
        today = date.today()
        obj0 = await self.model.create(date=today.isoformat())
        obj = await self.model.get(id=obj0.id)
        self.assertEqual(obj.date, today)

    async def test_values(self):
        today = date.today()
        obj0 = await self.model.create(date=today)
        values = await self.model.get(id=obj0.id).values("date")
        self.assertEqual(values["date"], today)

    async def test_values_list(self):
        today = date.today()
        obj0 = await self.model.create(date=today)
        values = await self.model.get(id=obj0.id).values_list("date", flat=True)
        self.assertEqual(values, today)

    async def test_get(self):
        today = date.today()
        await self.model.create(date=today)
        obj = await self.model.get(date=today)
        self.assertEqual(obj.date, today)

    async def test_date_str(self):
        obj0 = await self.model.create(date="2020-08-17")
        obj1 = await self.model.get(date="2020-08-17")
        self.assertEqual(obj0.date, obj1.date)
        with self.assertRaises((ParseError, ValueError)):
            await self.model.create(date="2020-08-xx")
        await self.model.filter(date="2020-08-17").update(date="2020-08-18")
        obj2 = await self.model.get(date="2020-08-18")
        self.assertEqual(obj2.date, date(year=2020, month=8, day=18))


class TestTimeDeltaFields(TestEmpty):
    model = testmodels.TimeDeltaFields

    async def test_create(self):
        obj0 = await self.model.create(timedelta=timedelta(days=35, seconds=8, microseconds=1))
        obj = await self.model.get(id=obj0.id)
        self.assertEqual(obj.timedelta, timedelta(days=35, seconds=8, microseconds=1))
        self.assertEqual(obj.timedelta_null, None)
        await obj.save()
        obj2 = await self.model.get(id=obj.id)
        self.assertEqual(obj, obj2)

    async def test_values(self):
        obj0 = await self.model.create(timedelta=timedelta(days=35, seconds=8, microseconds=1))
        values = await self.model.get(id=obj0.id).values("timedelta")
        self.assertEqual(values["timedelta"], timedelta(days=35, seconds=8, microseconds=1))

    async def test_values_list(self):
        obj0 = await self.model.create(timedelta=timedelta(days=35, seconds=8, microseconds=1))
        values = await self.model.get(id=obj0.id).values_list("timedelta", flat=True)
        self.assertEqual(values, timedelta(days=35, seconds=8, microseconds=1))

    async def test_get(self):
        delta = timedelta(days=35, seconds=8, microseconds=2)
        await self.model.create(timedelta=delta)
        obj = await self.model.get(timedelta=delta)
        self.assertEqual(obj.timedelta, delta)
