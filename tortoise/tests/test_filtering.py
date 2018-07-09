from tortoise.contrib import test
from tortoise.query_utils import Q
from tortoise.tests.testmodels import Event, Team, Tournament


class TestFiltering(test.TestCase):
    async def test_filtering(self):
        tournament = Tournament(name='Tournament')
        await tournament.save()

        second_tournament = Tournament(name='Tournament 2')
        await second_tournament.save()

        event_first = Event(name='1', tournament=tournament)
        await event_first.save()
        event_second = Event(name='2', tournament=second_tournament)
        await event_second.save()
        event_third = Event(name='3', tournament=tournament)
        await event_third.save()
        event_forth = Event(name='4', tournament=second_tournament)
        await event_forth.save()

        team_first = Team(name='First')
        await team_first.save()
        team_second = Team(name='Second')
        await team_second.save()

        await team_first.events.add(event_first)
        await event_second.participants.add(team_second)

        found_events = await Event.filter(
            Q(id__in=[event_first.id, event_second.id])
            | Q(name='3')
        ).filter(participants__not=team_second.id).order_by('name', 'tournament_id').distinct()
        self.assertEqual(len(found_events), 2)
        self.assertEqual(found_events[0].id, event_first.id)
        self.assertEqual(found_events[1].id, event_third.id)
        await Team.filter(events__tournament_id=tournament.id).order_by('-events__name')
        await Tournament.filter(
            events__name__in=['1', '3'],
        ).distinct()

        teams = await Team.filter(name__icontains='CON')
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0].name, 'Second')

        tournaments = await Tournament.filter(events__participants__name__startswith='Fir')
        self.assertEqual(len(tournaments), 1)
        self.assertEqual(tournaments[0], tournament)
