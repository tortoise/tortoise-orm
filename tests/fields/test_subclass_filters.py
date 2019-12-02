from tests.fields.subclass_models import RaceParticipant, RacePlacingEnum
from tortoise.contrib import test


class TestCustomFieldFilters(test.IsolatedTestCase):
    tortoise_test_modules = ["tests.fields.subclass_models"]

    async def setUp(self):
        await RaceParticipant.create(
            first_name="George", place=RacePlacingEnum.FIRST, predicted_place=RacePlacingEnum.SECOND
        )
        await RaceParticipant.create(
            first_name="John", place=RacePlacingEnum.SECOND, predicted_place=RacePlacingEnum.THIRD
        )
        await RaceParticipant.create(first_name="Paul", place=RacePlacingEnum.THIRD)
        await RaceParticipant.create(first_name="Ringo", place=RacePlacingEnum.RUNNER_UP)
        await RaceParticipant.create(first_name="Stuart", predicted_place=RacePlacingEnum.FIRST)

    async def test_equal(self):
        self.assertEqual(
            set(
                await RaceParticipant.filter(place=RacePlacingEnum.FIRST).values_list(
                    "place", flat=True
                )
            ),
            {RacePlacingEnum.FIRST},
        )

    async def test_not(self):
        self.assertEqual(
            set(
                await RaceParticipant.filter(place__not=RacePlacingEnum.FIRST).values_list(
                    "place", flat=True
                )
            ),
            {
                RacePlacingEnum.SECOND,
                RacePlacingEnum.THIRD,
                RacePlacingEnum.RUNNER_UP,
                RacePlacingEnum.DNF,
            },
        )

    async def test_in(self):
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(
                    place__in=[RacePlacingEnum.DNF, RacePlacingEnum.RUNNER_UP]
                ).values_list("place", flat=True)
            ),
            {RacePlacingEnum.DNF, RacePlacingEnum.RUNNER_UP},
        )

    async def test_not_in(self):
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(
                    place__not_in=[RacePlacingEnum.DNF, RacePlacingEnum.RUNNER_UP]
                ).values_list("place", flat=True)
            ),
            {RacePlacingEnum.FIRST, RacePlacingEnum.SECOND, RacePlacingEnum.THIRD},
        )

    async def test_isnull(self):
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(predicted_place__isnull=True).values_list(
                    "first_name", flat=True
                )
            ),
            {"Paul", "Ringo"},
        )
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(predicted_place__isnull=False).values_list(
                    "first_name", flat=True
                )
            ),
            {"George", "John", "Stuart"},
        )

    async def test_not_isnull(self):
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(predicted_place__not_isnull=False).values_list(
                    "first_name", flat=True
                )
            ),
            {"Paul", "Ringo"},
        )
        self.assertSetEqual(
            set(
                await RaceParticipant.filter(predicted_place__not_isnull=True).values_list(
                    "first_name", flat=True
                )
            ),
            {"George", "John", "Stuart"},
        )
