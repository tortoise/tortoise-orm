from datetime import datetime, timedelta

from tests.testmodels import DefaultUpdate, Event, Tournament
from tortoise.contrib import test


class TestUpdate(test.TestCase):
    async def test_update(self):
        await Tournament.create(name="1")
        await Tournament.create(name="3")
        rows_affected = await Tournament.all().update(name="2")
        self.assertEqual(rows_affected, 2)

        tournament = await Tournament.first()
        self.assertEqual(tournament.name, "2")

    async def test_update_auto_now(self):
        obj = await DefaultUpdate.create()

        now = datetime.now()
        updated_at = now - timedelta(days=1)
        await DefaultUpdate.filter(pk=obj.pk).update(updated_at=updated_at)

        obj1 = await DefaultUpdate.get(pk=obj.pk)
        self.assertEqual(obj1.updated_at.date(), updated_at.date())

    async def test_update_relation(self):
        tournament_first = await Tournament.create(name="1")
        tournament_second = await Tournament.create(name="2")

        await Event.create(name="1", tournament=tournament_first)
        await Event.all().update(tournament=tournament_second)
        event = await Event.first()
        self.assertEqual(event.tournament_id, tournament_second.id)
