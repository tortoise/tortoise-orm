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
