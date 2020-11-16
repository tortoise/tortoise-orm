import os
from datetime import datetime, tzinfo
from typing import Optional

import pytz


def get_use_tz() -> bool:
    """
    Get use_tz from env set in Tortoise config.
    """
    return os.environ.get("USE_TZ") == "True"


def get_timezone() -> str:
    """
    Get timezone from env set in Tortoise config.
    """
    return os.environ.get("TZ") or "UTC"


def now() -> datetime:
    """
    Return an aware datetime.datetime, depending on use_tz and timezone.
    """
    if get_use_tz():
        return datetime.now(tz=pytz.utc)
    else:
        return datetime.now(get_default_timezone())


def get_default_timezone() -> tzinfo:
    """
    Return the default time zone as a tzinfo instance.

    This is the time zone defined by Tortoise config.
    """
    return pytz.timezone(get_timezone())


def localtime(value: Optional[datetime] = None, timezone: Optional[str] = None) -> datetime:
    """
    Convert an aware datetime.datetime to local time.

    Only aware datetime are allowed. When value is omitted, it defaults to
    now().

    Local time is defined by the current time zone, unless another time zone
    is specified.

    :raises ValueError: when value is naive datetime
    """
    if value is None:
        value = now()
    if timezone is None:
        tz = get_default_timezone()
    else:
        tz = pytz.timezone(timezone)
    if is_naive(value):
        raise ValueError("localtime() cannot be applied to a naive datetime")
    return value.astimezone(tz)


def is_aware(value: datetime) -> bool:
    """
    Determine if a given datetime.datetime is aware.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def is_naive(value: datetime) -> bool:
    """
    Determine if a given datetime.datetime is naive.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is None


def make_aware(
    value: datetime, timezone: Optional[str] = None, is_dst: Optional[bool] = None
) -> datetime:
    """
    Make a naive datetime.datetime in a given time zone aware.

    :raises ValueError: when value is not naive datetime
    """
    if timezone is None:
        tz = get_default_timezone()
    else:
        tz = pytz.timezone(timezone)
    if hasattr(tz, "localize"):
        return tz.localize(value, is_dst=is_dst)  # type: ignore
    else:
        if is_aware(value):
            raise ValueError("make_aware expects a naive datetime, got %s" % value)
        # This may be wrong around DST changes!
        return value.replace(tzinfo=tz)


def make_native(value: datetime, timezone: Optional[str] = None) -> datetime:
    """
    Make an aware datetime.datetime naive in a given time zone.

    :raises ValueError: when value is naive datetime
    """
    if timezone is None:
        tz = get_default_timezone()
    else:
        tz = pytz.timezone(timezone)
    if is_naive(value):
        raise ValueError("make_naive() cannot be applied to a naive datetime")
    return value.astimezone(tz).replace(tzinfo=None)
