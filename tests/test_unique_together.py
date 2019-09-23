from tests.testmodels import Tournament, UniqueTogetherFields, UniqueTogetherFieldsWithFK
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError


class TestUniqueTogether(test.TestCase):
    async def test_unique_together(self):
        first_name = "first_name"
        last_name = "last_name"

        await UniqueTogetherFields.create(first_name=first_name, last_name=last_name)

        with self.assertRaises(IntegrityError):
            await UniqueTogetherFields.create(first_name=first_name, last_name=last_name)

    async def test_unique_together_with_foreign_keys(self):
        tournament_name = "tournament_name"
        text = "text"

        tournament = await Tournament.create(name=tournament_name)

        await UniqueTogetherFieldsWithFK.create(text=text, tournament=tournament)

        with self.assertRaises(IntegrityError):
            await UniqueTogetherFieldsWithFK.create(text=text, tournament=tournament)
