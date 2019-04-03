from tortoise.contrib import test
from tortoise.tests import testmodels


async def create_participants():
    test1 = await testmodels.RaceParticipant.create(
        first_name="Alex",
        place=testmodels.RacePlacingEnum.FIRST,
        predicted_place=testmodels.RacePlacingEnum.THIRD,
    )
    test2 = await testmodels.RaceParticipant.create(
        first_name="Ben",
        place=testmodels.RacePlacingEnum.SECOND,
        predicted_place=testmodels.RacePlacingEnum.FIRST,
    )
    test3 = await testmodels.RaceParticipant.create(
        first_name="Chris", place=testmodels.RacePlacingEnum.THIRD
    )
    test4 = await testmodels.RaceParticipant.create(first_name="Bill")

    return test1, test2, test3, test4


class TestEnumField(test.TestCase):
    """Tests the enumeration field."""

    async def test_enum_field_create(self):
        """Asserts that the new field is saved properly."""
        test1, _, _, _ = await create_participants()
        self.assertIn(test1, await testmodels.RaceParticipant.all())
        self.assertEqual(test1.place, testmodels.RacePlacingEnum.FIRST)

    async def test_enum_field_update(self):
        """Asserts that the new field can be updated correctly."""
        test1, _, _, _ = await create_participants()
        test1.place = testmodels.RacePlacingEnum.SECOND
        await test1.save()

        tied_second = await testmodels.RaceParticipant.filter(
            place=testmodels.RacePlacingEnum.SECOND
        )

        self.assertIn(test1, tied_second)
        self.assertEqual(len(tied_second), 2)

    async def test_enum_field_filter(self):
        """Assert that filters correctly select the enums."""
        await create_participants()

        first_place = await testmodels.RaceParticipant.filter(
            place=testmodels.RacePlacingEnum.FIRST
        ).first()

        second_place = await testmodels.RaceParticipant.filter(
            place=testmodels.RacePlacingEnum.SECOND
        ).first()

        self.assertEqual(first_place.place, testmodels.RacePlacingEnum.FIRST)
        self.assertEqual(second_place.place, testmodels.RacePlacingEnum.SECOND)

    async def test_enum_field_delete(self):
        """Assert that delete correctly removes the right participant by their place."""
        await create_participants()
        await testmodels.RaceParticipant.filter(place=testmodels.RacePlacingEnum.FIRST).delete()
        self.assertEqual(await testmodels.RaceParticipant.all().count(), 3)

    async def test_enum_field_default(self):
        _, _, _, test4 = await create_participants()
        self.assertEqual(test4.place, testmodels.RacePlacingEnum.DNF)

    async def test_enum_field_null(self):
        """Assert that filtering by None selects the records which are null."""
        _, _, test3, test4 = await create_participants()

        no_predictions = await testmodels.RaceParticipant.filter(predicted_place__isnull=True)

        self.assertIn(test3, no_predictions)
        self.assertIn(test4, no_predictions)
