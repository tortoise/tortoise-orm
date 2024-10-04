import unittest

from pypika import CustomFunction, FunctionException, Query, Table

__author__ = "Airton Zanon"
__email__ = "me@airton.dev"


class TestUnitCustomFunction(unittest.TestCase):
    def test_should_fail_with_wrong_arguments(self):
        DateDiff = CustomFunction("DATE_DIFF", ["interval", "start_date", "end_date"])

        with self.assertRaises(FunctionException):
            DateDiff("foo")

    def test_should_return_function_with_arguments(self):
        DateDiff = CustomFunction("DATE_DIFF", ["interval", "start_date", "end_date"])

        self.assertEqual(
            "DATE_DIFF('day','start_date','end_date')",
            str(DateDiff("day", "start_date", "end_date")),
        )

    def test_should_return_function_with_no_arguments(self):
        CurrentDate = CustomFunction("CURRENT_DATE")

        self.assertEqual("CURRENT_DATE()", str(CurrentDate()))


class TestFunctionalCustomFunction(unittest.TestCase):
    def test_should_use_custom_function_on_select(self):
        service = Table("service")

        DateDiff = CustomFunction("DATE_DIFF", ["interval", "start_date", "end_date"])

        q = Query.from_(service).select(DateDiff("day", service.created_date, service.updated_date))

        self.assertEqual(
            'SELECT DATE_DIFF(\'day\',"created_date","updated_date") FROM "service"',
            str(q),
        )

    def test_should_fail_use_custom_function_on_select_with_wrong_arguments(self):
        service = Table("service")

        DateDiff = CustomFunction("DATE_DIFF", ["interval", "start_date", "end_date"])

        with self.assertRaises(FunctionException):
            Query.from_(service).select(DateDiff("day", service.created_date))
