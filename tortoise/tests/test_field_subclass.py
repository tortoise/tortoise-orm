from tortoise.contrib import test
from tortoise.tests import testmodels


class TestEnumField(test.TestCase):

    async def test_enum_field_create(self):
        """Tests the enumeration field."""
        test1 = await testmodels.RaceParticipant.create(
            first_name="Alex",
            place=testmodels.RacePlacingEnum.FIRST)
        self.assertEqual(test1.place, testmodels.RacePlacingEnum.FIRST)

    async def test_enum_field_update(self):
        test1 = await testmodels.RaceParticipant.create(
            first_name="Alex",
            place=testmodels.RacePlacingEnum.FIRST)

        test1.place = testmodels.RacePlacingEnum.SECOND
        await test1.save()

        test2 = await testmodels.RaceParticipant.first()
        self.assertEqual(test1.place, test2.place)

    async def test_enum_field_filter(self):
        await testmodels.RaceParticipant.create(
            first_name="Alex",
            place=testmodels.RacePlacingEnum.FIRST)
        await testmodels.RaceParticipant.create(
            first_name="Ben",
            place=testmodels.RacePlacingEnum.SECOND)
        await testmodels.RaceParticipant.create(
            first_name="Chris",
            place=testmodels.RacePlacingEnum.THIRD)

        first_place = await testmodels.RaceParticipant \
            .filter(place=testmodels.RacePlacingEnum.FIRST) \
            .first()

        second_place = await testmodels.RaceParticipant \
            .filter(place=testmodels.RacePlacingEnum.SECOND) \
            .first()

        self.assertEqual(first_place.place, testmodels.RacePlacingEnum.FIRST)
        self.assertEqual(second_place.place, testmodels.RacePlacingEnum.SECOND)
