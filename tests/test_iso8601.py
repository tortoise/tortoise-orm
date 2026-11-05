from datetime import datetime
from datetime import timezone as dt_timezone

import pytest

from tortoise._iso8601 import parse_datetime


def test_parse_datetime_accepts_common_iso8601_forms():
    assert parse_datetime("2020-08-17") == datetime(2020, 8, 17)
    assert parse_datetime("2020-08-17T00:00:00Z") == datetime(2020, 8, 17, tzinfo=dt_timezone.utc)
    assert parse_datetime("2020-230T12:34:56Z") == datetime(
        2020, 8, 17, 12, 34, 56, tzinfo=dt_timezone.utc
    )
    assert parse_datetime("2020-230t12:34:56") == datetime(2020, 8, 17, 12, 34, 56)
    assert parse_datetime("2020230T123456") == datetime(2020, 8, 17, 12, 34, 56)


@pytest.mark.parametrize(
    "value",
    [
        "2020-08-17",
        "20200817",
        "2020-08-17T12:34:56",
        "2020-08-17t12:34:56",
        "2020-08-17 12:34:56",
        "20200817T123456",
        "2020-08-17T12:34:56Z",
        "2020-08-17T12:34:56z",
        "2020-08-17T12:34:56+08",
        "2020-08-17T12:34:56+0800",
        "2020-08-17T12:34:56+08:00",
        "2020-W34-1",
        "2020W341",
        "2020-230",
        "2020230",
        "2020-230T12:34:56",
        "2020-230t12:34:56",
        "2020230T123456",
    ],
)
def test_parse_datetime_matches_ciso8601(value):
    ciso8601 = pytest.importorskip("ciso8601")

    assert parse_datetime(value) == ciso8601.parse_datetime(value)


@pytest.mark.parametrize(
    "value",
    [
        "2020-13-01",
        "2020-367",
        "2021-02-29",
        "2020-W54-1",
    ],
)
def test_parse_datetime_rejects_invalid_dates(value):
    with pytest.raises(ValueError):
        parse_datetime(value)
