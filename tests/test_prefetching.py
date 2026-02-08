import pytest

from tests.testmodels import Address, Event, Team, Tournament
from tortoise.exceptions import FieldError, OperationalError
from tortoise.functions import Count
from tortoise.query_utils import Prefetch


@pytest.mark.asyncio
async def test_prefetch(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    await Event.create(name="Second", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    tournament = await Tournament.all().prefetch_related("events__participants").first()
    assert len(tournament.events[0].participants) == 2
    assert len(tournament.events[1].participants) == 0


@pytest.mark.asyncio
async def test_prefetch_object(db):
    tournament = await Tournament.create(name="tournament")
    await Event.create(name="First", tournament=tournament)
    await Event.create(name="Second", tournament=tournament)
    tournament_with_filtered = (
        await Tournament.all()
        .prefetch_related(Prefetch("events", queryset=Event.filter(name="First")))
        .first()
    )
    tournament = await Tournament.first().prefetch_related("events")
    assert len(tournament_with_filtered.events) == 1
    assert len(tournament.events) == 2


@pytest.mark.asyncio
async def test_prefetch_unknown_field(db):
    with pytest.raises(OperationalError):
        tournament = await Tournament.create(name="tournament")
        await Event.create(name="First", tournament=tournament)
        await Event.create(name="Second", tournament=tournament)
        await (
            Tournament.all()
            .prefetch_related(Prefetch("events1", queryset=Event.filter(name="First")))
            .first()
        )


@pytest.mark.asyncio
async def test_prefetch_m2m(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    fetched_events = (
        await Event.all()
        .prefetch_related(Prefetch("participants", queryset=Team.filter(name="1")))
        .first()
    )
    assert len(fetched_events.participants) == 1


@pytest.mark.asyncio
async def test_prefetch_o2o(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    await Address.create(city="Santa Monica", street="Ocean", event=event)

    fetched_events = await Event.all().prefetch_related("address").first()

    assert fetched_events.address.city == "Santa Monica"


@pytest.mark.asyncio
async def test_prefetch_nested(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    await Event.create(name="Second", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    fetched_tournaments = (
        await Tournament.all()
        .prefetch_related(
            Prefetch("events", queryset=Event.filter(name="First")),
            Prefetch("events__participants", queryset=Team.filter(name="1")),
        )
        .first()
    )
    assert len(fetched_tournaments.events[0].participants) == 1


@pytest.mark.asyncio
async def test_prefetch_nested_with_aggregation(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    await Event.create(name="Second", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    fetched_tournaments = (
        await Tournament.all()
        .prefetch_related(
            Prefetch("events", queryset=Event.annotate(teams=Count("participants")).filter(teams=2))
        )
        .first()
    )
    assert len(fetched_tournaments.events) == 1
    assert fetched_tournaments.events[0].pk == event.pk


@pytest.mark.asyncio
async def test_prefetch_direct_relation(db):
    tournament = await Tournament.create(name="tournament")
    await Event.create(name="First", tournament=tournament)
    event = await Event.first().prefetch_related("tournament")
    assert event.tournament.id == tournament.id


@pytest.mark.asyncio
async def test_prefetch_bad_key(db):
    tournament = await Tournament.create(name="tournament")
    await Event.create(name="First", tournament=tournament)
    with pytest.raises(FieldError, match="Relation tour1nament for models.Event not found"):
        await Event.first().prefetch_related("tour1nament")


@pytest.mark.asyncio
async def test_prefetch_m2m_filter(db):
    tournament = await Tournament.create(name="tournament")
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    event = await Event.create(name="First", tournament=tournament)
    await event.participants.add(team, team_second)
    event = await Event.first().prefetch_related(Prefetch("participants", Team.filter(name="2")))
    assert len(event.participants) == 1
    assert list(event.participants) == [team_second]


@pytest.mark.asyncio
async def test_prefetch_m2m_to_attr(db):
    tournament = await Tournament.create(name="tournament")
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    event = await Event.create(name="First", tournament=tournament)
    await event.participants.add(team, team_second)
    event = await Event.first().prefetch_related(
        Prefetch("participants", Team.filter(name="1"), to_attr="to_attr_participants_1"),
        Prefetch("participants", Team.filter(name="2"), to_attr="to_attr_participants_2"),
    )
    assert list(event.to_attr_participants_1) == [team]
    assert list(event.to_attr_participants_2) == [team_second]


@pytest.mark.asyncio
async def test_prefetch_o2o_to_attr(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    address = await Address.create(city="Santa Monica", street="Ocean", event=event)
    event = await Event.get(pk=event.pk).prefetch_related(
        Prefetch("address", to_attr="to_address", queryset=Address.all())
    )
    assert address.pk == event.to_address.pk


@pytest.mark.asyncio
async def test_prefetch_direct_relation_to_attr(db):
    tournament = await Tournament.create(name="tournament")
    await Event.create(name="First", tournament=tournament)
    event = await Event.first().prefetch_related(
        Prefetch("tournament", queryset=Tournament.all(), to_attr="to_attr_tournament")
    )
    assert event.to_attr_tournament.id == tournament.id
