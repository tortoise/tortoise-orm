from decimal import Decimal

from tests.testmodels import ValidatorModel
from tortoise.contrib import test
from tortoise.exceptions import ValidationError


class TestValues(test.TestCase):
    async def test_validator_regex(self):
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(regex="ccc")
        await ValidatorModel.create(regex="abcd")

    async def test_validator_max_length(self):
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(max_length="aaaaaa")
        await ValidatorModel.create(max_length="aaaaa")

    async def test_validator_min_value(self):
        # min value is 10
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(min_value=9)
        await ValidatorModel.create(min_value=10)

        # min value is Decimal("1.0")
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(min_value_decimal=Decimal("0.9"))
        await ValidatorModel.create(min_value_decimal=Decimal("1.0"))

    async def test_validator_max_value(self):
        # max value is 20
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(max_value=21)
        await ValidatorModel.create(max_value=20)

        # max value is Decimal("2.0")
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(max_value_decimal=Decimal("3.0"))
        await ValidatorModel.create(max_value_decimal=Decimal("2.0"))

    async def test_validator_ipv4(self):
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(ipv4="aaaaaa")
        await ValidatorModel.create(ipv4="8.8.8.8")

    async def test_validator_ipv6(self):
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(ipv6="aaaaaa")
        await ValidatorModel.create(ipv6="::")

    async def test_validator_comma_separated_integer_list(self):
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(comma_separated_integer_list="aaaaaa")
        await ValidatorModel.create(comma_separated_integer_list="1,2,3")

    async def test__prevent_saving(self):
        with self.assertRaises(ValidationError):
            await ValidatorModel.create(min_value_decimal=Decimal("0.9"))

        self.assertEqual(await ValidatorModel.all().count(), 0)

    async def test_save(self):
        with self.assertRaises(ValidationError):
            record = ValidatorModel(min_value_decimal=Decimal("0.9"))
            await record.save()

        record.min_value_decimal = Decimal("1.5")
        await record.save()

    async def test_save_with_update_fields(self):
        record = await ValidatorModel.create(min_value_decimal=Decimal("2"))

        record.min_value_decimal = Decimal("0.9")
        with self.assertRaises(ValidationError):
            await record.save(update_fields=["min_value_decimal"])

    async def test_update(self):
        record = await ValidatorModel.create(min_value_decimal=Decimal("2"))

        record.min_value_decimal = Decimal("0.9")
        with self.assertRaises(ValidationError):
            await record.save()
