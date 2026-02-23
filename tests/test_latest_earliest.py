import pytest
import pytest_asyncio

from tests.testmodels import Event, Tournament


@pytest_asyncio.fixture
async def latest_earliest_data(db):
    """Fixture to set up test data for latest/earliest tests."""
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


@pytest.mark.asyncio
async def test_latest(latest_earliest_data):
    assert await Event.latest("-name") == await Event.get(name="1")
    assert await Event.latest("name") == await Event.get(name="4")
    assert await Event.latest("-name") == await Event.all().order_by("name").first()
    assert await Event.latest("name") == await Event.all().order_by("-name").first()
    assert await Event.latest("tournament__name", "name") == await Event.get(name="4")
    assert await Event.latest("-tournament__name", "name") == await Event.get(name="3")
    assert await Event.latest("tournament__name", "-name") == await Event.get(name="2")
    assert await Event.latest("-tournament__name", "-name") == await Event.get(name="1")


@pytest.mark.asyncio
async def test_earliest(latest_earliest_data):
    assert await Event.earliest("name") == await Event.get(name="1")
    assert await Event.earliest("-name") == await Event.get(name="4")
    assert await Event.earliest("name") == await Event.all().order_by("name").first()
    assert await Event.earliest("-name") == await Event.all().order_by("-name").first()
    assert await Event.earliest("-tournament__name", "-name") == await Event.get(name="4")
    assert await Event.earliest("tournament__name", "-name") == await Event.get(name="3")
    assert await Event.earliest("-tournament__name", "name") == await Event.get(name="2")
    assert await Event.earliest("tournament__name", "name") == await Event.get(name="1")
