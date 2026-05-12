from __future__ import annotations

import abc
import ipaddress
import re
from decimal import Decimal
from functools import cached_property
from typing import Any
from urllib.parse import urlsplit

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


UL = "\u00a1-\uffff"
HOSTNAME_REGEX = r"[a-z" + UL + r"0-9](?:[a-z" + UL + r"0-9-]{0,61}[a-z" + UL + r"0-9])?"
# Max length for domain name labels is 63 characters per RFC 1034 sec. 3.1.
DOMAIN_REGEX = r"(?:\.(?!-)[a-z" + UL + r"0-9-]{1,63}(?<!-))*"
# Top-level domain.
TLD_NO_FQDN_REGEX = (
    r"\."  # dot
    r"(?!-)"  # can't start with a dash
    r"(?:[a-z" + UL + "-]{2,63}"  # domain label
    r"|xn--[a-z0-9]{1,59})"  # or punycode label
    r"(?<!-)"  # can't end with a dash
)
TLD_REGEX = TLD_NO_FQDN_REGEX + r"\.?"


class InvalidDomainName(ValidationError):
    def __init__(self) -> None:
        super().__init__("Invalid domain name")


class DomainNameValidator(Validator):
    """
    Validator for domain names.

    Validates domain names according to RFC 1034 and RFC 1123. Supports both
    ASCII domain names and internationalized domain names (IDN) when accept_idna
    is True.

    :param accept_idna: If True, accepts internationalized domain names (IDN).
                       Defaults to True.
    :raises InvalidDomainName: if the value is not a valid domain name.
    """

    ASCII_ONLY_HOSTNAME_REGEX = r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    ASCII_ONLY_DOMAIN_REGEX = r"(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*"
    ASCII_ONLY_TLD_REGEX = (
        r"\."  # dot
        r"(?!-)"  # can't start with a dash
        r"(?:[a-zA-Z0-9-]{2,63})"  # domain label
        r"(?<!-)"  # can't end with a dash
        r"\.?"  # may have a trailing dot
    )
    MAX_DOMAIN_LENGTH = 255

    @cached_property
    def _accept_idna_regex(self) -> re.Pattern[str]:
        return re.compile(r"^" + HOSTNAME_REGEX + DOMAIN_REGEX + TLD_REGEX + r"$", re.IGNORECASE)

    @cached_property
    def _do_not_accept_idna_regex(self) -> re.Pattern[str]:
        return re.compile(
            r"^"
            + self.ASCII_ONLY_HOSTNAME_REGEX
            + self.ASCII_ONLY_DOMAIN_REGEX
            + self.ASCII_ONLY_TLD_REGEX
            + r"$",
            re.IGNORECASE,
        )

    def __init__(self, accept_idna: bool = True) -> None:
        self.accept_idna = accept_idna
        self.regex = self._accept_idna_regex if accept_idna else self._do_not_accept_idna_regex

    def __call__(self, value: str) -> None:
        if len(value) > self.MAX_DOMAIN_LENGTH:
            raise InvalidDomainName()

        if not (self.accept_idna or value.isascii()):
            raise InvalidDomainName()

        if not self.regex.search(value):
            raise InvalidDomainName()


validate_domain_name = DomainNameValidator()
validate_domain_name.__doc__ = "Pre-configured DomainNameValidator instance."


class InvalidURL(ValidationError):
    def __init__(self, message: str = "Invalid URL") -> None:
        super().__init__(message)


class InvalidScheme(InvalidURL):
    def __init__(self, scheme: str) -> None:
        super().__init__(f"Invalid scheme: {scheme} is not allowed")


class URLValidator(Validator):
    """
    Validator for URLs.

    Validates URLs according to RFC 3986. Checks scheme, host, port, and path
    components. Supports HTTP, HTTPS, FTP, and FTPS schemes by default.

    :param allowed_schemes: List of allowed URL schemes. Defaults to ["http", "https", "ftp", "ftps"].
    :raises InvalidURL: if the value is not a valid URL.
    :raises InvalidScheme: if the URL scheme is not in the allowed list.
    """

    IPV4_REGEX = (
        r"(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)"
        r"(?:\.(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)){3}"
    )
    SIMPLE_IPV6_REGEX = r"\[[0-9a-f:.]+\]"  # (simple regex, validated later)
    ADVANCED_IPV6_REGEX = r"^\[(.+)\](?::[0-9]{1,5})?$"
    HOST_REGEX = "(" + HOSTNAME_REGEX + DOMAIN_REGEX + TLD_REGEX + "|localhost)"
    URL_REGEX = (
        r"^(?:[a-z0-9.+-]*)://"  # scheme is validated separately
        r"(?:[^\s:@/]+(?::[^\s:@/]*)?@)?"  # user:pass authentication
        r"(?:" + IPV4_REGEX + "|" + SIMPLE_IPV6_REGEX + "|" + HOST_REGEX + ")"
        r"(?::[0-9]{1,5})?"  # port
        r"(?:[/?#][^\s]*)?"  # resource path
        r"\Z"
    )
    UNSAFE_CHARS = frozenset("\t\r\n")
    MAX_URL_LENGTH = 2048

    # The maximum length of a full host name is 253 characters per RFC 1034
    # section 3.1. It's defined to be 255 bytes or fewer, but this includes
    # one byte for the length of the name and one byte for the trailing dot
    # that's used to indicate absolute names in DNS.
    MAX_HOSTNAME_LENGTH = 253

    @cached_property
    def _url_regex(self) -> re.Pattern[str]:
        return re.compile(self.URL_REGEX, re.IGNORECASE)

    def __init__(self, allowed_schemes: list[str] | None = None) -> None:
        self.allowed_schemes = allowed_schemes or ["http", "https", "ftp", "ftps"]

    def __call__(self, value: str) -> None:
        if len(value) > self.MAX_URL_LENGTH:
            raise InvalidURL()

        if self.UNSAFE_CHARS.intersection(value):
            raise InvalidURL()

        try:
            split_url = urlsplit(value)
        except ValueError:
            raise InvalidURL()

        if split_url.scheme.lower() not in self.allowed_schemes:
            raise InvalidScheme(split_url.scheme.lower())

        if split_url.hostname is None or len(split_url.hostname) > self.MAX_HOSTNAME_LENGTH:
            raise InvalidURL()

        if not self._url_regex.search(value):
            raise InvalidURL()

        # Now verify IPv6 in the netloc part
        host_match = re.search(self.ADVANCED_IPV6_REGEX, split_url.netloc)
        if host_match:
            potential_ip = host_match[1]
            try:
                validate_ipv6_address(potential_ip)
            except ValidationError:
                raise InvalidURL()


validate_url = URLValidator()
validate_url.__doc__ = "Pre-configured URLValidator instance."


class InvalidEmailAddress(ValidationError):
    def __init__(self) -> None:
        super().__init__("Invalid email address")


class EmailValidator(Validator):
    """
    Validator for email addresses.

    Validates email addresses according to RFC 3696. Checks both the local part
    (before @) and domain part (after @). Supports domain allowlisting for
    restricting to specific domains.

    :param allowed_domains: List of allowed domain names. If provided, only emails
                            from these domains will be accepted.
    :raises InvalidEmailAddress: if the value is not a valid email address.
    """

    # The maximum length of an email is 320 characters per RFC 3696 section 3
    MAX_EMAIL_LENGTH = 320

    USER_REGEX = (
        # dot-atom
        r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*\Z"
        # quoted-string
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])'
        r'*"\Z)'
    )
    LITERAL_REGEX = (
        # literal form, ipv4 or ipv6 address (SMTP 4.1.3)
        r"\[([A-F0-9:.]+)\]\Z"
    )

    @cached_property
    def _user_regex(self) -> re.Pattern[str]:
        return re.compile(self.USER_REGEX, re.IGNORECASE)

    @cached_property
    def _domain_regex(self) -> re.Pattern[str]:
        print("evaluating domain regex!!!")
        return re.compile(
            r"^" + HOSTNAME_REGEX + DOMAIN_REGEX + TLD_NO_FQDN_REGEX + r"\Z", re.IGNORECASE
        )

    @cached_property
    def _literal_regex(self) -> re.Pattern[str]:
        return re.compile(self.LITERAL_REGEX, re.IGNORECASE)

    def _validate_domain_part(self, domain_part: str) -> bool:
        if self._domain_regex.match(domain_part):
            return True

        if literal_match := self._literal_regex.match(domain_part):
            ip_address = literal_match[1]
            try:
                validate_ipv46_address(ip_address)
                return True
            except ValidationError:
                pass
        return False

    def __init__(self, allowed_domains: list[str] | None = None) -> None:
        self.allowed_domains: list[str] = allowed_domains or []

    def __call__(self, value: str) -> None:
        if "@" not in value or len(value) > self.MAX_EMAIL_LENGTH:
            raise InvalidEmailAddress()

        user_part, domain_part = value.rsplit("@", 1)

        if not self._user_regex.match(user_part):
            raise InvalidEmailAddress()

        if domain_part not in self.allowed_domains and not self._validate_domain_part(domain_part):
            raise InvalidEmailAddress()


validate_email = EmailValidator()
validate_email.__doc__ = "Pre-configured EmailValidator instance."


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
