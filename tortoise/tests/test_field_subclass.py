from tortoise.contrib import test
from tortoise.tests import testmodels


class TestEnumField(test.TestCase):

    async def test_enum_field(self):
        """Tests the enumeration field."""
        test1 = await testmodels.RaceParticipant.create(first_name="Alex", place=testmodels.RacePlacingEnum.FIRST)
        self.assertEquals(test1.place, testmodels.RacePlacingEnum.FIRST)

        test1.place = testmodels.RacePlacingEnum.SECOND
        await test1.save()

        test2 = await testmodels.RaceParticipant.first()
        self.assertEquals(test1.place, test2.place)

        test3 = await testmodels.RaceParticipant.filter(place=testmodels.RacePlacingEnum.SECOND).first()
        self.assertEquals(test1.place, test3.place)
