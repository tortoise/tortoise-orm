from __future__ import annotations

import functools
import os
import sys
from datetime import datetime, time, tzinfo
from zoneinfo import ZoneInfo as _ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

if sys.version_info >= (3, 12):
    from datetime import UTC
else:
    from datetime import timezone

    UTC = timezone.utc


class ZoneInfo(_ZoneInfo):
    @property
    def zone(self) -> str:
        # Compatible with pytz:
        # >>> ZoneInfo('UTC').key == pytz.timezone('UTC').zone == 'UTC'
        return self.key


def parse_timezone(zone: str) -> tzinfo:
    if zone.upper() == "UTC":
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(zone)
    except ZoneInfoNotFoundError as e:
        words = zone.split("/")
        # Compatible with `pytz.timezone`:
        #   US/central -> US/Central
        #   Europe/moscow -> Europe/Moscow
        #   asia/ShangHai -> Asia/Shanghai
        styled = "/".join([i if i.isupper() else i.title() for i in words])
        if styled != zone:
            return ZoneInfo(styled)
        raise e


@functools.cache
def get_use_tz() -> bool:
    """
    Get use_tz from env set in Tortoise config.
    """
    return os.environ.get("USE_TZ") == "True"


@functools.cache
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
        return datetime.now(tz=UTC)
    else:
        return datetime.now(get_default_timezone())


@functools.cache
def get_default_timezone() -> tzinfo:
    """
    Return the default time zone as a tzinfo instance.

    This is the time zone defined by Tortoise config.
    """
    return parse_timezone(get_timezone())


def _reset_timezone_cache() -> None:
    """Reset timezone cache. For internal use only."""
    get_default_timezone.cache_clear()
    get_use_tz.cache_clear()
    get_timezone.cache_clear()


def _get_or_parse_timezone(timezone: tzinfo | str | None = None) -> tzinfo:
    """
    If timezone is None return get_default_timezone()
    else if timezone is tzinfo object, return it;
    else parse string to ZoneInfo instance.
    """
    if timezone is None:
        return get_default_timezone()
    return parse_timezone(timezone) if isinstance(timezone, str) else timezone


def localtime(value: datetime | None = None, timezone: tzinfo | str | None = None) -> datetime:
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
    elif is_naive(value):
        raise ValueError("localtime() cannot be applied to a naive datetime")
    tz = _get_or_parse_timezone(timezone)
    return value.astimezone(tz)


def is_aware(value: datetime | time) -> bool:
    """
    Determine if a given datetime.datetime or datetime.time is aware.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def is_naive(value: datetime | time) -> bool:
    """
    Determine if a given datetime.datetime or datetime.time is naive.

    The concept is defined in Python's docs:
    https://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is None


def make_aware(
    value: datetime, timezone: tzinfo | str | None = None, is_dst: bool | None = None
) -> datetime:
    """
    Make a naive datetime.datetime in a given time zone aware.

    :raises ValueError: when value is not naive datetime
    """
    tz = _get_or_parse_timezone(timezone)
    if hasattr(tz, "localize"):
        return tz.localize(value, is_dst=is_dst)
    if is_aware(value):
        raise ValueError(f"make_aware expects a naive datetime, got {value}")
    # This may be wrong around DST changes!
    return value.replace(tzinfo=tz)


def make_naive(value: datetime, timezone: tzinfo | str | None = None) -> datetime:
    """
    Make an aware datetime.datetime naive in a given time zone.

    :raises ValueError: when value is naive datetime
    """
    tz = _get_or_parse_timezone(timezone)
    if is_naive(value):
        raise ValueError("make_naive() cannot be applied to a naive datetime")
    return value.astimezone(tz).replace(tzinfo=None)
