from tests.testmodels import Event, Tournament
from tortoise.contrib import test


class TestLatestEarliest(test.TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        tournament = Tournament(name="Tournament 1")
        await tournament.save()

        second_tournament = Tournament(name="Tournament 2")
        await second_tournament.save()

        event_first = Event(name="1", tournament=tournament)
        await event_first.save()
        event_second = Event(name="2", tournament=second_tournament)
        await event_second.save()
        event_third = Event(name="3", tournament=tournament)
        await event_third.save()
        event_forth = Event(name="4", tournament=second_tournament)
        await event_forth.save()

    async def test_latest(self):
        self.assertEqual(await Event.latest("-name"), await Event.get(name="1"))
        self.assertEqual(await Event.latest("name"), await Event.get(name="4"))
        self.assertEqual(await Event.latest("-name"), await Event.all().order_by("name").first())
        self.assertEqual(await Event.latest("name"), await Event.all().order_by("-name").first())
        self.assertEqual(await Event.latest("tournament__name", "name"), await Event.get(name="4"))
        self.assertEqual(await Event.latest("-tournament__name", "name"), await Event.get(name="3"))
        self.assertEqual(await Event.latest("tournament__name", "-name"), await Event.get(name="2"))
        self.assertEqual(
            await Event.latest("-tournament__name", "-name"), await Event.get(name="1")
        )

    async def test_earliest(self):
        self.assertEqual(await Event.earliest("name"), await Event.get(name="1"))
        self.assertEqual(await Event.earliest("-name"), await Event.get(name="4"))
        self.assertEqual(await Event.earliest("name"), await Event.all().order_by("name").first())
        self.assertEqual(await Event.earliest("-name"), await Event.all().order_by("-name").first())
        self.assertEqual(
            await Event.earliest("-tournament__name", "-name"), await Event.get(name="4")
        )
        self.assertEqual(
            await Event.earliest("tournament__name", "-name"), await Event.get(name="3")
        )
        self.assertEqual(
            await Event.earliest("-tournament__name", "name"), await Event.get(name="2")
        )
        self.assertEqual(
            await Event.earliest("tournament__name", "name"), await Event.get(name="1")
        )
