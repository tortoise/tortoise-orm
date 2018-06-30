import unittest

from tortoise import fields
from tortoise.exceptions import FieldError


class TestFieldErrors(unittest.TestCase):

    def test_decimal_field_neg_digits(self):
        with self.assertRaises(FieldError):
            fields.DecimalField(-1, 2)

    def test_decimal_field_neg_decimal(self):
        with self.assertRaises(FieldError):
            fields.DecimalField(2, -1)

    def test_datetime_field_auto_bad(self):
        with self.assertRaises(FieldError):
            fields.DatetimeField(auto_now=True, auto_now_add=True)
