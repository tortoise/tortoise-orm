from unittest import skipIf

from tortoise.contrib import test
from tortoise.utils import parse_datetime

try:
    import ciso8601
except ImportError:
    ciso8601 = None


@skipIf(not ciso8601, "Library 'ciso8601' is required")
class TestParseDatetime(test.TestCase):
    def test_no_timezone(self):
        cases = [
            "2026-01-13",
            "2026-01-14 00:00:01",
            "2026-01-15 01:23:45.123456",
        ]
        for time_str in cases:
            assert parse_datetime(time_str) == ciso8601.parse_datetime(time_str)

    def test_with_timezone(self):
        cases = [
            "2026-01-14T00:00:01Z",
            "2026-01-15T01:23:45.123456+08:00",
            "2026-01-15T01:23:45-05:30",
        ]
        for time_str in cases:
            assert parse_datetime(time_str) == ciso8601.parse_datetime(time_str)
