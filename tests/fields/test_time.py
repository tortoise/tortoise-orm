import contextlib
import os
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from time import sleep
from unittest.mock import patch
from zoneinfo import ZoneInfoNotFoundError

import pytest
from iso8601 import ParseError

from tests import testmodels
from tortoise import fields, timezone
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotIn
from tortoise.exceptions import ConfigurationError, IntegrityError
from tortoise.expressions import F
from tortoise.timezone import UTC, ZoneInfo, get_default_timezone, parse_timezone

# ============================================================================
# TestEmpty -> test_empty_*
# ============================================================================


@pytest.mark.asyncio
async def test_empty_datetime_fields(db):
    """Test that creating DatetimeFields without required field raises IntegrityError."""
    with pytest.raises(IntegrityError):
        await testmodels.DatetimeFields.create()


# ============================================================================
# TestDatetimeFields -> test_datetime_*
# ============================================================================


@pytest.fixture(autouse=True)
def reset_timezone_cache():
    """Reset timezone cache before and after each test."""
    timezone._reset_timezone_cache()
    yield
    timezone._reset_timezone_cache()


def test_datetime_both_auto_bad(db):
    """Test that setting both auto_now and auto_now_add raises ConfigurationError."""
    with pytest.raises(
        ConfigurationError, match="You can choose only 'auto_now' or 'auto_now_add'"
    ):
        fields.DatetimeField(auto_now=True, auto_now_add=True)


@pytest.mark.asyncio
async def test_datetime_create(db):
    """Test creating datetime fields and auto_now/auto_now_add behavior."""
    model = testmodels.DatetimeFields
    now = timezone.now()
    obj0 = await model.create(datetime=now)
    obj = await model.get(id=obj0.id)
    assert obj.datetime == now
    assert obj.datetime_null is None
    assert obj.datetime_auto - now < timedelta(microseconds=20000)
    assert obj.datetime_add - now < timedelta(microseconds=20000)
    datetime_auto = obj.datetime_auto
    sleep(0.012)
    await obj.save()
    obj2 = await model.get(id=obj.id)
    assert obj2.datetime == now
    assert obj2.datetime_null is None
    assert obj2.datetime_auto == obj.datetime_auto
    assert obj2.datetime_auto != datetime_auto
    assert obj2.datetime_auto - now > timedelta(microseconds=10000)
    assert obj2.datetime_auto - now < timedelta(seconds=1)
    assert obj2.datetime_add == obj.datetime_add


@pytest.mark.asyncio
async def test_datetime_update(db):
    """Test updating datetime fields via filter().update()."""
    model = testmodels.DatetimeFields
    obj0 = await model.create(datetime=datetime(2019, 9, 1, 0, 0, 0, tzinfo=get_default_timezone()))
    await model.filter(id=obj0.id).update(
        datetime=datetime(2019, 9, 1, 6, 0, 8, tzinfo=get_default_timezone())
    )
    obj = await model.get(id=obj0.id)
    assert obj.datetime == datetime(2019, 9, 1, 6, 0, 8, tzinfo=get_default_timezone())
    assert obj.datetime_null is None


@pytest.mark.asyncio
async def test_datetime_filter(db):
    """Test filtering by datetime field."""
    model = testmodels.DatetimeFields
    now = timezone.now()
    obj = await model.create(datetime=now)
    assert await model.filter(datetime=now).first() == obj
    assert await model.annotate(d=F("datetime")).filter(d=now).first() == obj


@pytest.mark.asyncio
async def test_datetime_cast(db):
    """Test datetime field accepts ISO format string."""
    model = testmodels.DatetimeFields
    now = timezone.now()
    obj0 = await model.create(datetime=now.isoformat())
    obj = await model.get(id=obj0.id)
    assert obj.datetime == now


@pytest.mark.asyncio
async def test_datetime_values(db):
    """Test datetime field in values() query."""
    model = testmodels.DatetimeFields
    now = timezone.now()
    obj0 = await model.create(datetime=now)
    values = await model.get(id=obj0.id).values("datetime")
    assert values["datetime"] == now


@pytest.mark.asyncio
async def test_datetime_values_list(db):
    """Test datetime field in values_list() query."""
    model = testmodels.DatetimeFields
    now = timezone.now()
    obj0 = await model.create(datetime=now)
    values = await model.get(id=obj0.id).values_list("datetime", flat=True)
    assert values == now


@pytest.mark.asyncio
async def test_datetime_get_utcnow(db):
    """Test getting datetime using UTC now."""
    model = testmodels.DatetimeFields
    now = datetime.now(dt_timezone.utc).replace(tzinfo=get_default_timezone())
    await model.create(datetime=now)
    obj = await model.get(datetime=now)
    assert obj.datetime == now


@pytest.mark.asyncio
async def test_datetime_get_now(db):
    """Test getting datetime using timezone.now()."""
    model = testmodels.DatetimeFields
    now = timezone.now()
    await model.create(datetime=now)
    obj = await model.get(datetime=now)
    assert obj.datetime == now


@pytest.mark.asyncio
async def test_datetime_count(db):
    """Test count queries with datetime fields."""
    model = testmodels.DatetimeFields
    now = timezone.now()
    obj = await model.create(datetime=now)
    assert await model.filter(datetime=obj.datetime).count() == 1
    assert await model.filter(datetime_auto=obj.datetime_auto).count() == 1
    assert await model.filter(datetime_add=obj.datetime_add).count() == 1


@pytest.mark.asyncio
async def test_datetime_default_timezone(db):
    """Test default timezone is UTC."""
    model = testmodels.DatetimeFields
    now = timezone.now()
    obj = await model.create(datetime=now)
    assert obj.datetime.tzinfo.zone == "UTC"

    obj_get = await model.get(pk=obj.pk)
    assert obj_get.datetime.tzinfo.zone == "UTC"
    assert obj_get.datetime == now


@pytest.mark.asyncio
async def test_datetime_set_timezone(db):
    """Test setting a custom timezone via environment variable."""
    model = testmodels.DatetimeFields
    old_tz = os.environ["TIMEZONE"]
    tz = "Asia/Shanghai"
    os.environ["TIMEZONE"] = tz
    now = datetime.now(parse_timezone(tz))
    obj = await model.create(datetime=now)
    assert obj.datetime.tzinfo.zone == tz

    obj_get = await model.get(pk=obj.pk)
    assert obj_get.datetime.tzinfo.zone == tz
    assert obj_get.datetime == now

    os.environ["TIMEZONE"] = old_tz


@pytest.mark.asyncio
async def test_datetime_timezone(db):
    """Test timezone handling with USE_TZ enabled."""
    model = testmodels.DatetimeFields
    old_tz = os.environ["TIMEZONE"]
    old_use_tz = os.environ["USE_TZ"]
    tz = "Asia/Shanghai"
    os.environ["TIMEZONE"] = tz
    os.environ["USE_TZ"] = "True"

    now = datetime.now(parse_timezone(tz))
    obj = await model.create(datetime=now)
    assert obj.datetime.tzinfo.zone == tz
    obj_get = await model.get(pk=obj.pk)
    assert obj.datetime.tzinfo.zone == tz
    assert obj_get.datetime == now

    os.environ["TIMEZONE"] = old_tz
    os.environ["USE_TZ"] = old_use_tz


@pytest.mark.asyncio
@test.requireCapability(dialect=NotIn("sqlite", "mssql"))
async def test_datetime_filter_by_year_month_day(db):
    """Test filtering datetime by year, month, and day."""
    model = testmodels.DatetimeFields
    with patch.dict(os.environ, {"USE_TZ": "True"}):
        obj = await model.create(datetime=datetime(2024, 1, 2))
        same_year_objs = await model.filter(datetime__year=2024)
        filtered_obj = await model.filter(
            datetime__year=2024, datetime__month=1, datetime__day=2
        ).first()
        assert obj == filtered_obj
        assert obj.id in [i.id for i in same_year_objs]


# ============================================================================
# TestTimeFields (postgres) -> test_time_*
# ============================================================================


@pytest.mark.asyncio
@test.requireCapability(dialect=NotIn("sqlite"))  # 'datetime.time' is not supported by sqlite3
@test.requireCapability(dialect="postgres")
async def test_time_create(db):
    """Test creating time fields (postgres)."""
    model = testmodels.TimeFields
    now = timezone.now().timetz()
    obj0 = await model.create(time=now)
    obj1 = await model.get(id=obj0.id)
    assert obj1.time == now


@pytest.mark.asyncio
@test.requireCapability(dialect=NotIn("sqlite"))  # 'datetime.time' is not supported by sqlite3
@test.requireCapability(dialect="postgres")
async def test_time_cast(db):
    """Test time field accepts ISO format string (postgres)."""
    model = testmodels.TimeFields
    obj0 = await model.create(time="21:00+00:00")
    obj1 = await model.get(id=obj0.id)
    assert obj1.time == time.fromisoformat("21:00+00:00")


@pytest.mark.asyncio
@test.requireCapability(dialect=NotIn("sqlite"))  # 'datetime.time' is not supported by sqlite3
@test.requireCapability(dialect="postgres")
async def test_time_values(db):
    """Test time field in values() query (postgres)."""
    model = testmodels.TimeFields
    now = timezone.now().timetz()
    obj0 = await model.create(time=now)
    values = await model.get(id=obj0.id).values("time")
    assert values["time"] == now


@pytest.mark.asyncio
@test.requireCapability(dialect=NotIn("sqlite"))  # 'datetime.time' is not supported by sqlite3
@test.requireCapability(dialect="postgres")
async def test_time_values_list(db):
    """Test time field in values_list() query (postgres)."""
    model = testmodels.TimeFields
    now = timezone.now().timetz()
    obj0 = await model.create(time=now)
    values = await model.get(id=obj0.id).values_list("time", flat=True)
    assert values == now


@pytest.mark.asyncio
@test.requireCapability(dialect=NotIn("sqlite"))  # 'datetime.time' is not supported by sqlite3
@test.requireCapability(dialect="postgres")
async def test_time_get(db):
    """Test getting by time field (postgres)."""
    model = testmodels.TimeFields
    now = timezone.now().timetz()
    await model.create(time=now)
    obj = await model.get(time=now)
    assert obj.time == now


# ============================================================================
# TestTimeFieldsMySQL -> test_time_mysql_*
# ============================================================================


@pytest.mark.asyncio
@test.requireCapability(dialect="mysql")
async def test_time_mysql_create(db):
    """Test creating time fields (mysql returns timedelta)."""
    model = testmodels.TimeFields
    now = timezone.now().timetz()
    obj0 = await model.create(time=now)
    obj1 = await model.get(id=obj0.id)
    assert obj1.time == timedelta(
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second,
        microseconds=now.microsecond,
    )


@pytest.mark.asyncio
@test.requireCapability(dialect="mysql")
async def test_time_mysql_cast(db):
    """Test time field accepts ISO format string (mysql returns timedelta)."""
    model = testmodels.TimeFields
    obj0 = await model.create(time="21:00+00:00")
    obj1 = await model.get(id=obj0.id)
    t = time.fromisoformat("21:00+00:00")
    assert obj1.time == timedelta(
        hours=t.hour,
        minutes=t.minute,
        seconds=t.second,
        microseconds=t.microsecond,
    )


@pytest.mark.asyncio
@test.requireCapability(dialect="mysql")
async def test_time_mysql_values(db):
    """Test time field in values() query (mysql returns timedelta)."""
    model = testmodels.TimeFields
    now = timezone.now().timetz()
    obj0 = await model.create(time=now)
    values = await model.get(id=obj0.id).values("time")
    assert values["time"] == timedelta(
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second,
        microseconds=now.microsecond,
    )


@pytest.mark.asyncio
@test.requireCapability(dialect="mysql")
async def test_time_mysql_values_list(db):
    """Test time field in values_list() query (mysql returns timedelta)."""
    model = testmodels.TimeFields
    now = timezone.now().timetz()
    obj0 = await model.create(time=now)
    values = await model.get(id=obj0.id).values_list("time", flat=True)
    assert values == timedelta(
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second,
        microseconds=now.microsecond,
    )


@pytest.mark.asyncio
@test.requireCapability(dialect="mysql")
async def test_time_mysql_get(db):
    """Test getting by time field (mysql returns timedelta)."""
    model = testmodels.TimeFields
    now = timezone.now().timetz()
    await model.create(time=now)
    obj = await model.get(time=now)
    assert obj.time == timedelta(
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second,
        microseconds=now.microsecond,
    )


# ============================================================================
# TestDateFields -> test_date_*
# ============================================================================


@pytest.mark.asyncio
async def test_empty_date_fields(db):
    """Test that creating DateFields without required field raises IntegrityError."""
    with pytest.raises(IntegrityError):
        await testmodels.DateFields.create()


@pytest.mark.asyncio
async def test_date_create(db):
    """Test creating date fields."""
    model = testmodels.DateFields
    today = date.today()
    obj0 = await model.create(date=today)
    obj = await model.get(id=obj0.id)
    assert obj.date == today
    assert obj.date_null is None
    await obj.save()
    obj2 = await model.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_date_cast(db):
    """Test date field accepts ISO format string."""
    model = testmodels.DateFields
    today = date.today()
    obj0 = await model.create(date=today.isoformat())
    obj = await model.get(id=obj0.id)
    assert obj.date == today


@pytest.mark.asyncio
async def test_date_values(db):
    """Test date field in values() query."""
    model = testmodels.DateFields
    today = date.today()
    obj0 = await model.create(date=today)
    values = await model.get(id=obj0.id).values("date")
    assert values["date"] == today


@pytest.mark.asyncio
async def test_date_values_list(db):
    """Test date field in values_list() query."""
    model = testmodels.DateFields
    today = date.today()
    obj0 = await model.create(date=today)
    values = await model.get(id=obj0.id).values_list("date", flat=True)
    assert values == today


@pytest.mark.asyncio
async def test_date_get(db):
    """Test getting by date field."""
    model = testmodels.DateFields
    today = date.today()
    await model.create(date=today)
    obj = await model.get(date=today)
    assert obj.date == today


@pytest.mark.asyncio
async def test_date_str(db):
    """Test date field with string input and filtering/updating."""
    model = testmodels.DateFields
    obj0 = await model.create(date="2020-08-17")
    obj1 = await model.get(date="2020-08-17")
    assert obj0.date == obj1.date
    with pytest.raises((ParseError, ValueError)):
        await model.create(date="2020-08-xx")
    await model.filter(date="2020-08-17").update(date="2020-08-18")
    obj2 = await model.get(date="2020-08-18")
    assert obj2.date == date(year=2020, month=8, day=18)


# ============================================================================
# TestTimeDeltaFields -> test_timedelta_*
# ============================================================================


@pytest.mark.asyncio
async def test_empty_timedelta_fields(db):
    """Test that creating TimeDeltaFields without required field raises IntegrityError."""
    with pytest.raises(IntegrityError):
        await testmodels.TimeDeltaFields.create()


@pytest.mark.asyncio
async def test_timedelta_create(db):
    """Test creating timedelta fields."""
    model = testmodels.TimeDeltaFields
    obj0 = await model.create(timedelta=timedelta(days=35, seconds=8, microseconds=1))
    obj = await model.get(id=obj0.id)
    assert obj.timedelta == timedelta(days=35, seconds=8, microseconds=1)
    assert obj.timedelta_null is None
    await obj.save()
    obj2 = await model.get(id=obj.id)
    assert obj == obj2


@pytest.mark.asyncio
async def test_timedelta_values(db):
    """Test timedelta field in values() query."""
    model = testmodels.TimeDeltaFields
    obj0 = await model.create(timedelta=timedelta(days=35, seconds=8, microseconds=1))
    values = await model.get(id=obj0.id).values("timedelta")
    assert values["timedelta"] == timedelta(days=35, seconds=8, microseconds=1)


@pytest.mark.asyncio
async def test_timedelta_values_list(db):
    """Test timedelta field in values_list() query."""
    model = testmodels.TimeDeltaFields
    obj0 = await model.create(timedelta=timedelta(days=35, seconds=8, microseconds=1))
    values = await model.get(id=obj0.id).values_list("timedelta", flat=True)
    assert values == timedelta(days=35, seconds=8, microseconds=1)


@pytest.mark.asyncio
async def test_timedelta_get(db):
    """Test getting by timedelta field."""
    model = testmodels.TimeDeltaFields
    delta = timedelta(days=35, seconds=8, microseconds=2)
    await model.create(timedelta=delta)
    obj = await model.get(timedelta=delta)
    assert obj.timedelta == delta


def test_zoneinfo():
    tz = parse_timezone("Asia/Shanghai")
    tz2 = parse_timezone("asia/shanghai")
    tz3 = parse_timezone("asia/ShangHai")
    now = datetime.now()
    assert now.replace(tzinfo=tz) == now.replace(tzinfo=tz2) == now.replace(tzinfo=tz3)
    tz = parse_timezone("US/central")
    tz2 = parse_timezone("US/Central")
    assert now.replace(tzinfo=tz) == now.replace(tzinfo=tz2)
    tz_utc = parse_timezone("UTC")
    tz_utc2 = parse_timezone("utc")
    tz_utc3 = parse_timezone("Utc")
    assert tz_utc.key == tz_utc2.zone == "UTC"
    assert (
        now.replace(tzinfo=UTC)
        == now.replace(tzinfo=tz_utc)
        == now.replace(tzinfo=tz_utc2)
        == now.replace(tzinfo=tz_utc3)
    )
    with pytest.raises(ZoneInfoNotFoundError):
        parse_timezone("invalid-zone-name")
    with pytest.raises(ZoneInfoNotFoundError):
        parse_timezone("Invalid/Zonename")


def test_timezone():
    # test localtime
    assert timezone.localtime() <= timezone.now() <= timezone.localtime()
    utcnow = datetime.now(UTC)
    tz_shanghai = ZoneInfo("Asia/Shanghai")
    assert timezone.localtime(utcnow).utcoffset() == timezone.now().utcoffset()
    localtime_shanghai = timezone.localtime(utcnow, tz_shanghai.key)
    assert timezone.localtime(utcnow, tz_shanghai) == localtime_shanghai
    assert localtime_shanghai.utcoffset() != timezone.localtime(utcnow, "UTC").utcoffset()
    naive_dt = datetime.now()
    with pytest.raises(ValueError):
        timezone.localtime(naive_dt)
    # test make_naive
    assert timezone.make_naive(timezone.now()).tzinfo is None
    with pytest.raises(ValueError):
        timezone.make_naive(naive_dt)
    tz_shanghai = ZoneInfo("Asia/Shanghai")
    now_shanghai = datetime.now(tz_shanghai)
    offset = now_shanghai.utcoffset()
    naive_now = timezone.make_naive(utcnow, tz_shanghai.key)
    assert (utcnow + offset).isoformat().split("+")[0] == naive_now.isoformat()
    # test make_aware
    with pytest.raises(ValueError):
        timezone.make_aware(utcnow)
    aware_now = timezone.make_aware(naive_now, tz_shanghai.key)
    assert aware_now.utcoffset() == now_shanghai.utcoffset()
    assert "+" in timezone.make_aware(naive_now).isoformat()
    # test compatible with pytz
    with contextlib.suppress(ImportError):
        import pytz

        aware_now = timezone.make_aware(naive_now, pytz.timezone(tz_shanghai.key))
        assert aware_now.utcoffset() == now_shanghai.utcoffset()
        pytz_shanghai = pytz.timezone(tz_shanghai.key)
        assert pytz_shanghai.zone == tz_shanghai.zone == tz_shanghai.key
        assert localtime_shanghai == timezone.localtime(utcnow, pytz_shanghai)
        assert (
            localtime_shanghai.utcoffset() == timezone.localtime(timezone=pytz_shanghai).utcoffset()
        )
