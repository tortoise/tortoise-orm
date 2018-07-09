from tortoise.contrib import test
from tortoise.query_utils import Prefetch
from tortoise.tests.testmodels import Event, Tournament


class TestPrefetching(test.TestCase):
    async def test_prefetching(self):
        tournament = await Tournament.create(name='tournament')
        await Event.create(name='First', tournament=tournament)
        await Event.create(name='Second', tournament=tournament)
        tournament_with_filtered = await Tournament.all().prefetch_related(
            Prefetch('events', queryset=Event.filter(name='First'))
        ).first()
        tournament = await Tournament.first().prefetch_related('events')
        self.assertEqual(len(tournament_with_filtered.events), 1)
        self.assertEqual(len(tournament.events), 2)
