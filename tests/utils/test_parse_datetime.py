from unittest import skipIf

import pytest

from tortoise.contrib import test
from tortoise.utils import parse_datetime

try:
    import ciso8601
except ImportError:
    ciso8601 = None  # type: ignore[assignment]


@skipIf(not ciso8601, "Library 'ciso8601' is required")
class TestParseDatetime(test.TestCase):
    def test_no_timezone(self):
        cases = [
            "20260101",
            "2026-01-13",
            "20260113 01",
            "20260113 0102",
            "20260113 010203",
            "2026-01-14 00:00:01",
            "2026-01-15 01:23:45.12345",
            "2026-01-15 01:23:45.123456",
        ]
        for time_str in cases:
            assert ciso8601.parse_datetime(time_str) == parse_datetime(time_str)
        for invalid in ["2026-00-00", "26-01-02"]:
            with pytest.raises(ValueError):
                ciso8601.parse_datetime(invalid)
            with pytest.raises(ValueError):
                parse_datetime(invalid)

    def test_with_timezone(self):
        cases = [
            "2026-01-14T00:00:01z",
            "2026-01-14T00:00:01Z",
            "2026-01-15T01:23:45.123456+08:00",
            "2026-01-15T01:23:45-05:30",
        ]
        for time_str in cases:
            assert ciso8601.parse_datetime(time_str) == parse_datetime(time_str)
        for invalid_zone in ["+00:001", "+25:00"]:
            invalid = "2026-01-14T00:00:00" + invalid_zone
            with pytest.raises(ValueError):
                ciso8601.parse_datetime(invalid)
            with pytest.raises(ValueError):
                parse_datetime(invalid)
