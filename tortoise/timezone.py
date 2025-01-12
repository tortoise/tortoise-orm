import os
from datetime import datetime, time, tzinfo
from functools import lru_cache
from typing import Optional, Union

import pytz


@lru_cache(maxsize=None)
def get_use_tz() -> bool:
    """
    Get use_tz from env set in Tortoise config.
    """
    return os.environ.get("USE_TZ") == "True"


@lru_cache(maxsize=None)
def get_timezone() -> str:
    """
    Get timezone from env set in Tortoise config.
    """
    return os.environ.get("TIMEZONE") or "UTC"


def now() -> datetime:
    """
    Return an aware datetime.datetime, depending on use_tz and timezone.
    """
    if get_use_tz():
        return datetime.now(tz=pytz.utc)
    else:
        return datetime.now(get_default_timezone())


@lru_cache(maxsize=None)
def get_default_timezone() -> tzinfo:
    """
    Return the default time zone as a tzinfo instance.

    This is the time zone defined by Tortoise config.
    """
    return pytz.timezone(get_timezone())


def _reset_timezone_cache() -> None:
    """Reset timezone cache. For internal use only."""
    get_default_timezone.cache_clear()
    get_use_tz.cache_clear()
    get_timezone.cache_clear()


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
    tz = get_default_timezone() if timezone is None else pytz.timezone(timezone)
    if is_naive(value):
        raise ValueError("localtime() cannot be applied to a naive datetime")
    return value.astimezone(tz)


def is_aware(value: Union[datetime, time]) -> bool:
    """
    Determine if a given datetime.datetime or datetime.time is aware.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def is_naive(value: Union[datetime, time]) -> bool:
    """
    Determine if a given datetime.datetime or datetime.time is naive.

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
    tz = get_default_timezone() if timezone is None else pytz.timezone(timezone)
    if hasattr(tz, "localize"):
        return tz.localize(value, is_dst=is_dst)
    if is_aware(value):
        raise ValueError("make_aware expects a naive datetime, got %s" % value)
    # This may be wrong around DST changes!
    return value.replace(tzinfo=tz)


def make_naive(value: datetime, timezone: Optional[str] = None) -> datetime:
    """
    Make an aware datetime.datetime naive in a given time zone.

    :raises ValueError: when value is naive datetime
    """
    tz = get_default_timezone() if timezone is None else pytz.timezone(timezone)
    if is_naive(value):
        raise ValueError("make_naive() cannot be applied to a naive datetime")
    return value.astimezone(tz).replace(tzinfo=None)
