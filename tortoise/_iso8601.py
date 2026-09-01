from __future__ import annotations

import re
from datetime import datetime, timedelta

_CALENDAR_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?=$|[Tt ])")
_BASIC_CALENDAR_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(?=$|[Tt ])")
_ORDINAL_DATE_RE = re.compile(r"^(\d{4})-(\d{3})(?=$|[Tt ])")
_BASIC_ORDINAL_DATE_RE = re.compile(r"^(\d{4})(\d{3})(?=$|[Tt ])")
_WEEK_DATE_RE = re.compile(r"^(\d{4})-W(\d{2})(?:-(\d))?(?=$|[Tt ])")
_BASIC_WEEK_DATE_RE = re.compile(r"^(\d{4})W(\d{2})(\d)?(?=$|[Tt ])")
_BASIC_TIME_RE = re.compile(r"^(\d{2})(\d{2})?(\d{2})?([.,]\d+)?(?=$|[+-])")
_TZ_OFFSET_RE = re.compile(r"([+-])(\d{2})(?::?(\d{2}))?$")


def _normalize_timezone_offset(value: str) -> str:
    if m := _TZ_OFFSET_RE.search(value):
        return f"{value[: m.start()]}{m[1]}{m[2]}:{m[3] or '00'}"
    return value


def _normalize_datetime_suffix(value: str, *, allow_basic_time: bool) -> str:
    if not value:
        return value

    sep, time_value = value[0], _normalize_timezone_offset(value[1:])
    if allow_basic_time and (m := _BASIC_TIME_RE.match(time_value)):
        minute = m[2] or "00"
        second = f":{m[3]}" if m[3] else ""
        fraction = m[4] or ""
        time_value = f"{m[1]}:{minute}{second}{fraction}{time_value[m.end() :]}"
    return f"{sep}{time_value}"


def _ordinal_date(year: str, day: str) -> datetime:
    year_int, day_int = int(year), int(day)
    value = datetime(year_int, 1, 1) + timedelta(days=day_int - 1)
    if day_int < 1 or value.year != year_int:
        raise ValueError(f"Invalid ordinal day: {day_int} is out of range for year {year_int}")
    return value


def parse_datetime(value: str) -> datetime:
    if value.endswith(("Z", "z")):
        value = f"{value[:-1]}+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        if m := _CALENDAR_DATE_RE.match(value):
            date_value = datetime(int(m[1]), int(m[2]), int(m[3])).date()
            suffix = _normalize_datetime_suffix(value[m.end() :], allow_basic_time=False)
            return datetime.fromisoformat(f"{date_value.isoformat()}{suffix}")
        if m := _BASIC_CALENDAR_DATE_RE.match(value):
            date_value = datetime(int(m[1]), int(m[2]), int(m[3])).date()
            suffix = _normalize_datetime_suffix(value[m.end() :], allow_basic_time=True)
            return datetime.fromisoformat(f"{date_value.isoformat()}{suffix}")
        if m := _ORDINAL_DATE_RE.match(value):
            date_value = _ordinal_date(m[1], m[2]).date()
            suffix = _normalize_datetime_suffix(value[m.end() :], allow_basic_time=False)
            return datetime.fromisoformat(f"{date_value.isoformat()}{suffix}")
        if m := _BASIC_ORDINAL_DATE_RE.match(value):
            date_value = _ordinal_date(m[1], m[2]).date()
            suffix = _normalize_datetime_suffix(value[m.end() :], allow_basic_time=True)
            return datetime.fromisoformat(f"{date_value.isoformat()}{suffix}")
        if m := _WEEK_DATE_RE.match(value):
            date_value = datetime.fromisocalendar(int(m[1]), int(m[2]), int(m[3] or 1)).date()
            suffix = _normalize_datetime_suffix(value[m.end() :], allow_basic_time=False)
            return datetime.fromisoformat(f"{date_value.isoformat()}{suffix}")
        if m := _BASIC_WEEK_DATE_RE.match(value):
            date_value = datetime.fromisocalendar(int(m[1]), int(m[2]), int(m[3] or 1)).date()
            suffix = _normalize_datetime_suffix(value[m.end() :], allow_basic_time=True)
            return datetime.fromisoformat(f"{date_value.isoformat()}{suffix}")
        raise
