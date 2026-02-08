from __future__ import annotations

import abc
import ipaddress
import re
from decimal import Decimal
from typing import Any

from tortoise.exceptions import ValidationError


class Validator(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __call__(self, value: Any) -> None:
        """
        All specific validators should implement this method.

        :param value: The given value to be validated.
        :raises ValidationError: if validation failed.
        """


class RegexValidator(Validator):
    """
    A validator to validate the given value whether match regex or not.
    """

    def __init__(self, pattern: str, flags: int | re.RegexFlag) -> None:
        self.regex = re.compile(pattern, flags)

    def __call__(self, value: Any) -> None:
        if not self.regex.match(value):
            raise ValidationError(f"Value '{value}' does not match regex '{self.regex.pattern}'")


class MaxLengthValidator(Validator):
    """
    A validator to validate the length of given value whether greater than max_length or not.
    """

    def __init__(self, max_length: int) -> None:
        self.max_length = max_length

    def __call__(self, value: str) -> None:
        if value is None:
            raise ValidationError("Value must not be None")
        if len(value) > self.max_length:
            raise ValidationError(f"Length of '{value}' {len(value)} > {self.max_length}")


class MinLengthValidator(Validator):
    """
    A validator to validate the length of given value whether less than min_length or not.
    """

    def __init__(self, min_length: int) -> None:
        self.min_length = min_length

    def __call__(self, value: str) -> None:
        if value is None:
            raise ValidationError("Value must not be None")
        if len(value) < self.min_length:
            raise ValidationError(f"Length of '{value}' {len(value)} < {self.min_length}")


class NumericValidator(Validator):
    types = (int, float, Decimal)

    def _validate_type(self, value: Any) -> None:
        if not isinstance(value, self.types):
            raise ValidationError("Value must be a numeric value and is required")


class MinValueValidator(NumericValidator):
    """
    Min value validator for FloatField, IntField, SmallIntField, BigIntField
    """

    def __init__(self, min_value: int | float | Decimal) -> None:
        self._validate_type(min_value)
        self.min_value = min_value

    def __call__(self, value: int | float | Decimal) -> None:
        self._validate_type(value)
        if value < self.min_value:
            raise ValidationError(f"Value should be greater or equal to {self.min_value}")


class MaxValueValidator(NumericValidator):
    """
    Max value validator for FloatField, IntField, SmallIntField, BigIntField
    """

    def __init__(self, max_value: int | float | Decimal) -> None:
        self._validate_type(max_value)
        self.max_value = max_value

    def __call__(self, value: int | float | Decimal) -> None:
        self._validate_type(value)
        if value > self.max_value:
            raise ValidationError(f"Value should be less or equal to {self.max_value}")


class CommaSeparatedIntegerListValidator(Validator):
    """
    A validator to validate whether the given value is valid comma separated integer list or not.
    """

    def __init__(self, allow_negative: bool = False) -> None:
        pattern = r"^{neg}\d+(?:{sep}{neg}\d+)*\Z".format(
            neg="(-)?" if allow_negative else "",
            sep=re.escape(","),
        )
        self.regex = RegexValidator(pattern, re.I)

    def __call__(self, value: str) -> None:
        self.regex(value)


def validate_ipv4_address(value: Any) -> None:
    """
    A validator to validate whether the given value is valid IPv4Address or not.

    :raises ValidationError: if value is invalid IPv4Address.
    """

    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid IPv4 address.")


def validate_ipv6_address(value: Any) -> None:
    """
    A validator to validate whether the given value is valid IPv6Address or not.

    :raises ValidationError: if value is invalid IPv6Address.
    """
    try:
        ipaddress.IPv6Address(value)
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid IPv6 address.")


def validate_ipv46_address(value: Any) -> None:
    """
    A validator to validate whether the given value is valid IPv4Address or IPv6Address or not.

    :raises ValidationError: if value is invalid IPv4Address or IPv6Address.
    """
    try:
        validate_ipv4_address(value)
    except ValidationError:
        try:
            validate_ipv6_address(value)
        except ValidationError:
            raise ValidationError(f"'{value}' is not a valid IPv4 or IPv6 address.")
