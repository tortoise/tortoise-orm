from tests.testmodels import Contact, ContactTypeEnum, Event, Tournament
from tortoise.contrib import test


class TestUpdate(test.TestCase):
    async def test_update(self):
        await Tournament.create(name="1")
        await Tournament.all().update(name="2")

        tournament = await Tournament.first()
        self.assertEqual(tournament.name, "2")

    async def test_update_relation(self):
        tournament_first = await Tournament.create(name="1")
        tournament_second = await Tournament.create(name="2")

        await Event.create(name="1", tournament=tournament_first)
        await Event.all().update(tournament=tournament_second)
        event = await Event.first()
        self.assertEqual(event.tournament_id, tournament_second.id)

    async def test_update_with_int_enum_value(self):
        contact = await Contact.create()
        contact.type = ContactTypeEnum.home
        await contact.save()

    async def test_exception_on_invalid_data_type_in_int_field(self):
        contact = await Contact.create()

        contact.type = "not_int"
        with self.assertRaises((TypeError, ValueError)):
            await contact.save()
