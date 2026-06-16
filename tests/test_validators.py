from decimal import Decimal

import pytest

from tests.testmodels import ValidatorModel
from tortoise.exceptions import ValidationError


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
