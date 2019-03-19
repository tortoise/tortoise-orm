from tortoise.contrib import test
from tortoise.exceptions import IntegrityError
from tortoise.tests.testmodels import UniqueTogetherFields


class TestUniqueTogether(test.TestCase):
    async def test_unique_together(self):
        first_name = 'first_name'
        last_name = 'last_name'

        await UniqueTogetherFields.create(
            first_name=first_name,
            last_name=last_name
        )

        with self.assertRaises(IntegrityError):
            await UniqueTogetherFields.create(
                first_name=first_name,
                last_name=last_name
            )
