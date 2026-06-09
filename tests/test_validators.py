from decimal import Decimal

import pytest

from tests.testmodels import ValidatorModel
from tortoise.exceptions import ValidationError
from tortoise.validators import (
    DomainNameValidator,
    EmailValidator,
    InvalidDomainName,
    InvalidEmailAddress,
    InvalidScheme,
    InvalidURL,
    URLValidator,
    validate_domain_name,
    validate_email,
    validate_url,
)


@pytest.mark.asyncio
async def test_validator_regex(db):
    with pytest.raises(ValidationError):
        await ValidatorModel.create(regex="ccc")
    await ValidatorModel.create(regex="abcd")


@pytest.mark.asyncio
async def test_validator_max_length(db):
    with pytest.raises(ValidationError):
        await ValidatorModel.create(max_length="aaaaaa")
    await ValidatorModel.create(max_length="aaaaa")


@pytest.mark.asyncio
async def test_validator_min_length(db):
    with pytest.raises(ValidationError, match="Length of 'aa' 2 < 3"):
        await ValidatorModel.create(min_length="aa")
    await ValidatorModel.create(min_length="aaaa")


@pytest.mark.asyncio
async def test_validator_min_value(db):
    # min value is 10
    with pytest.raises(ValidationError):
        await ValidatorModel.create(min_value=9)
    await ValidatorModel.create(min_value=10)

    # min value is Decimal("1.0")
    with pytest.raises(ValidationError):
        await ValidatorModel.create(min_value_decimal=Decimal("0.9"))
    await ValidatorModel.create(min_value_decimal=Decimal("1.0"))


@pytest.mark.asyncio
async def test_validator_max_value(db):
    # max value is 20
    with pytest.raises(ValidationError):
        await ValidatorModel.create(max_value=21)
    await ValidatorModel.create(max_value=20)

    # max value is Decimal("2.0")
    with pytest.raises(ValidationError):
        await ValidatorModel.create(max_value_decimal=Decimal("3.0"))
    await ValidatorModel.create(max_value_decimal=Decimal("2.0"))


@pytest.mark.asyncio
async def test_validator_ipv4(db):
    with pytest.raises(ValidationError):
        await ValidatorModel.create(ipv4="aaaaaa")
    await ValidatorModel.create(ipv4="8.8.8.8")


@pytest.mark.asyncio
async def test_validator_ipv6(db):
    with pytest.raises(ValidationError):
        await ValidatorModel.create(ipv6="aaaaaa")
    await ValidatorModel.create(ipv6="::")


@pytest.mark.asyncio
async def test_validator_ipv46(db):
    with pytest.raises(ValidationError, match="'aaaaaa' is not a valid IPv4 or IPv6 address."):
        await ValidatorModel.create(ipv46="aaaaaa")
    await ValidatorModel.create(ipv46="::")
    await ValidatorModel.create(ipv46="8.8.8.8")


@pytest.mark.asyncio
async def test_validator_comma_separated_integer_list(db):
    with pytest.raises(ValidationError):
        await ValidatorModel.create(comma_separated_integer_list="aaaaaa")
    await ValidatorModel.create(comma_separated_integer_list="1,2,3")


@pytest.mark.asyncio
async def test_prevent_saving(db):
    with pytest.raises(ValidationError):
        await ValidatorModel.create(min_value_decimal=Decimal("0.9"))

    assert await ValidatorModel.all().count() == 0


@pytest.mark.asyncio
async def test_save(db):
    with pytest.raises(ValidationError):
        record = ValidatorModel(min_value_decimal=Decimal("0.9"))
        await record.save()

    record.min_value_decimal = Decimal("1.5")
    await record.save()


@pytest.mark.asyncio
async def test_save_with_update_fields(db):
    record = await ValidatorModel.create(min_value_decimal=Decimal("2"))

    record.min_value_decimal = Decimal("0.9")
    with pytest.raises(ValidationError):
        await record.save(update_fields=["min_value_decimal"])


@pytest.mark.asyncio
async def test_update(db):
    record = await ValidatorModel.create(min_value_decimal=Decimal("2"))

    record.min_value_decimal = Decimal("0.9")
    with pytest.raises(ValidationError):
        await record.save()


@pytest.mark.parametrize(
    "value",
    [
        "example.com",
        "sub.example.com",
        "example.co.uk",
        "münchen.de",
        "sub1.sub2.example.org",
        "UPPER-CASE.is.ok.net",
        "tortoise.github.io",
        "example.space",
        "❤️.website",
    ],
)
def test_domain_name_validator_valid(value):
    validate_domain_name(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "---.com",
        "example-.com",
        "under_line.com",
        "💻.tech",
    ],
)
def test_domain_name_validator_invalid(value):
    with pytest.raises(InvalidDomainName):
        validate_domain_name(value)


def test_domain_name_validator_invalid_idn_disabled():
    validator = DomainNameValidator(accept_idna=False)
    with pytest.raises(InvalidDomainName):
        validator("münchen.de")


@pytest.mark.parametrize(
    "value",
    [
        "http://example.com",
        "https://www.example.com/path?query=1",
        "ftp://ftp.example.com/file.txt",
        "http://localhost:8080",
        "http://192.168.1.1",
        "http://8.8.8.8:8080",
        "https://[::1]",
        "https://[2001:db8::1]:443",
        "http://user:pass@example.com",
        "http://example.com#fragment",
    ],
)
def test_url_validator_valid(value):
    validate_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "http://example.com",
        "https://example.com",
    ],
)
def test_url_validator_valid_custom_schemes(value):
    validator = URLValidator(allowed_schemes=["http", "https"])
    validator(value)


def test_url_validator_invalid_scheme():
    validator = URLValidator(allowed_schemes=["http", "https"])
    with pytest.raises(InvalidScheme):
        validator("ftp://example.com")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-a-url",
        "http://",
        "http:// space.com",
        "http://[::gggg]",
        "http://256.1.1.1",
        "http://" + "a" * 254 + ".com",
    ],
)
def test_url_validator_invalid(value):
    with pytest.raises(InvalidURL):
        validate_url(value)


def test_url_validator_max_length():
    long_url = "http://example.com/" + "a" * 2100
    with pytest.raises(InvalidURL):
        validate_url(long_url)


@pytest.mark.parametrize(
    "value",
    [
        "user@example.com",
        "user.name@example.com",
        "user+tag@example.co.uk",
        "user@sub.domain.com",
        "user@[192.168.1.1]",
        "user@[::1]",
        "a+b@example.com",
        "a-b@example.com",
        "a_b@example.com",
        "test@test.co.uk",
    ],
)
def test_email_validator_valid(value):
    validate_email(value)


def test_email_validator_valid_allowed_domains():
    validator = EmailValidator(allowed_domains=["example.com", "test.com"])
    validator("user@example.com")
    validator("user@test.com")


def test_email_validator_invalid_allowed_domains():
    validator = EmailValidator(allowed_domains=["example.com"])
    validator("user@example.com")
    with pytest.raises(InvalidEmailAddress):
        validator("user@")
    with pytest.raises(InvalidEmailAddress):
        validator("user@invalid..com")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-an-email",
        "user@",
        "@example.com",
        "user@.com",
        "user@com.",
        "user@com..com",
        "a" * 330 + "@example.com",
    ],
)
def test_email_validator_invalid(value):
    with pytest.raises(InvalidEmailAddress):
        validate_email(value)
