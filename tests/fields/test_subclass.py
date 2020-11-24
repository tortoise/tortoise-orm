from tests.fields.subclass_models import Contact, ContactTypeEnum, RaceParticipant, RacePlacingEnum
from tortoise.contrib import test


async def create_participants():
    test1 = await RaceParticipant.create(
        first_name="Alex",
        place=RacePlacingEnum.FIRST,
        predicted_place=RacePlacingEnum.THIRD,
    )
    test2 = await RaceParticipant.create(
        first_name="Ben",
        place=RacePlacingEnum.SECOND,
        predicted_place=RacePlacingEnum.FIRST,
    )
    test3 = await RaceParticipant.create(first_name="Chris", place=RacePlacingEnum.THIRD)
    test4 = await RaceParticipant.create(first_name="Bill")

    return test1, test2, test3, test4


class TestEnumField(test.IsolatedTestCase):
    """Tests the enumeration field."""

    tortoise_test_modules = ["tests.fields.subclass_models"]

    async def test_enum_field_create(self):
        """Asserts that the new field is saved properly."""
        test1, _, _, _ = await create_participants()
        self.assertIn(test1, await RaceParticipant.all())
        self.assertEqual(test1.place, RacePlacingEnum.FIRST)

    async def test_enum_field_update(self):
        """Asserts that the new field can be updated correctly."""
        test1, _, _, _ = await create_participants()
        test1.place = RacePlacingEnum.SECOND
        await test1.save()

        tied_second = await RaceParticipant.filter(place=RacePlacingEnum.SECOND)

        self.assertIn(test1, tied_second)
        self.assertEqual(len(tied_second), 2)

    async def test_enum_field_filter(self):
        """Assert that filters correctly select the enums."""
        await create_participants()

        first_place = await RaceParticipant.filter(place=RacePlacingEnum.FIRST).first()

        second_place = await RaceParticipant.filter(place=RacePlacingEnum.SECOND).first()

        self.assertEqual(first_place.place, RacePlacingEnum.FIRST)
        self.assertEqual(second_place.place, RacePlacingEnum.SECOND)

    async def test_enum_field_delete(self):
        """Assert that delete correctly removes the right participant by their place."""
        await create_participants()
        await RaceParticipant.filter(place=RacePlacingEnum.FIRST).delete()
        self.assertEqual(await RaceParticipant.all().count(), 3)

    async def test_enum_field_default(self):
        _, _, _, test4 = await create_participants()
        self.assertEqual(test4.place, RacePlacingEnum.DNF)

    async def test_enum_field_null(self):
        """Assert that filtering by None selects the records which are null."""
        _, _, test3, test4 = await create_participants()

        no_predictions = await RaceParticipant.filter(predicted_place__isnull=True)

        self.assertIn(test3, no_predictions)
        self.assertIn(test4, no_predictions)

    async def test_update_with_int_enum_value(self):
        contact = await Contact.create()
        contact.type = ContactTypeEnum.home
        await contact.save()

    async def test_exception_on_invalid_data_type_in_int_field(self):
        contact = await Contact.create()

        contact.type = "not_int"
        with self.assertRaises((TypeError, ValueError)):
            await contact.save()
