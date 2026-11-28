import pytest

from tests.testmodels import Event, Team, Tournament
from tortoise.query_utils import Prefetch


@pytest.mark.asyncio
async def test_prefetch_related_accumulates_across_calls(db):
    tournament = await Tournament.create(name="tournament")
    team = await Team.create(name="1")
    event = await Event.create(name="First", tournament=tournament)
    await event.participants.add(team)

    fetched = (
        await Event.filter(pk=event.pk)
        .prefetch_related("tournament")
        .prefetch_related("participants")
        .get()
    )
    assert fetched.tournament == tournament
    assert list(fetched.participants) == [team]


@pytest.mark.asyncio
async def test_prefetch_related_accumulates_strings_and_prefetches(db):
    tournament = await Tournament.create(name="tournament")
    team = await Team.create(name="1")
    event = await Event.create(name="First", tournament=tournament)
    await event.participants.add(team)

    fetched = (
        await Event.filter(pk=event.pk)
        .prefetch_related(Prefetch("participants", Team.all(), to_attr="teams"))
        .prefetch_related("tournament")
        .get()
    )
    assert fetched.tournament == tournament
    assert list(fetched.teams) == [team]


@pytest.mark.asyncio
async def test_prefetch_related_does_not_share_state_with_source_queryset(db):
    tournament = await Tournament.create(name="tournament")
    team = await Team.create(name="1")
    event = await Event.create(name="First", tournament=tournament)
    await event.participants.add(team)

    source = Event.filter(pk=event.pk).prefetch_related("tournament")
    derived = source.prefetch_related("participants")

    from_source = await source.get()
    assert from_source.tournament == tournament
    assert not isinstance(from_source.participants, list)

    from_derived = await derived.get()
    assert from_derived.tournament == tournament
    assert list(from_derived.participants) == [team]
