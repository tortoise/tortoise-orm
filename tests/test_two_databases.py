import os

import pytest
import pytest_asyncio

from tests.testmodels import Event, EventTwo, TeamTwo, Tournament
from tortoise.context import TortoiseContext
from tortoise.exceptions import OperationalError, ParamsError
from tortoise.transactions import in_transaction

# Optional import for Oracle client that requires system dependencies
try:
    from tortoise.backends.oracle import OracleClient
except ImportError:
    OracleClient = None  # type: ignore[misc,assignment]


@pytest_asyncio.fixture(scope="function")
async def two_databases():
    """Fixture that sets up two separate databases for testing."""
    db_url = os.getenv("TORTOISE_TEST_DB", "sqlite://:memory:")

    from tortoise.backends.base.config_generator import expand_db_url

    # Expand the URL with uniqueness if it's a template
    # This ensures "models" and "events" get different DB names if TORTOISE_TEST_DB has {}
    db1_config = expand_db_url(db_url, testing=True)
    db2_config = expand_db_url(db_url, testing=True)

    ctx = TortoiseContext()
    async with ctx:
        await ctx.init(
            config={
                "connections": {
                    "models": db1_config,
                    "events": db2_config,
                },
                "apps": {
                    "models": {"models": ["tests.testmodels"], "default_connection": "models"},
                    "events": {"models": ["tests.testmodels"], "default_connection": "events"},
                },
            },
            _create_db=True,
        )
        await ctx.generate_schemas()

        db = ctx.connections.get("models")
        second_db = ctx.connections.get("events")

        yield db, second_db


def build_select_sql(db) -> str:
    """Helper function to build SELECT SQL based on database type."""
    if OracleClient is not None and isinstance(db, OracleClient):
        return 'SELECT * FROM "eventtwo"'
    return "SELECT * FROM eventtwo"


@pytest.mark.asyncio
async def test_two_databases(two_databases):
    db, second_db = two_databases

    tournament = await Tournament.create(name="Tournament")
    await EventTwo.create(name="Event", tournament_id=tournament.id)

    select_sql = build_select_sql(db)
    with pytest.raises(OperationalError):
        await db.execute_query(select_sql)
    _, results = await second_db.execute_query(select_sql)
    assert dict(results[0]) == {"id": 1, "name": "Event", "tournament_id": 1}


@pytest.mark.asyncio
async def test_two_databases_relation(two_databases):
    db, second_db = two_databases

    tournament = await Tournament.create(name="Tournament")
    event = await EventTwo.create(name="Event", tournament_id=tournament.id)

    select_sql = build_select_sql(db)
    with pytest.raises(OperationalError):
        await db.execute_query(select_sql)

    _, results = await second_db.execute_query(select_sql)
    assert dict(results[0]) == {"id": 1, "name": "Event", "tournament_id": 1}

    teams = []
    for i in range(2):
        team = await TeamTwo.create(name=f"Team {(i + 1)}")
        teams.append(team)
        await event.participants.add(team)

    assert await TeamTwo.all().order_by("name") == teams
    assert await event.participants.all().order_by("name") == teams

    assert await TeamTwo.all().order_by("name").values("id", "name") == [
        {"id": 1, "name": "Team 1"},
        {"id": 2, "name": "Team 2"},
    ]
    assert await event.participants.all().order_by("name").values("id", "name") == [
        {"id": 1, "name": "Team 1"},
        {"id": 2, "name": "Team 2"},
    ]


@pytest.mark.asyncio
async def test_two_databases_transactions_switch_db(two_databases):
    async with in_transaction("models"):
        tournament = await Tournament.create(name="Tournament")
        await Event.create(name="Event1", tournament=tournament)
        async with in_transaction("events"):
            event = await EventTwo.create(name="Event2", tournament_id=tournament.id)
            team = await TeamTwo.create(name="Team 1")
            await event.participants.add(team)

    saved_tournament = await Tournament.filter(name="Tournament").first()
    assert tournament.id == saved_tournament.id
    saved_event = await EventTwo.filter(tournament_id=tournament.id).first()
    assert event.id == saved_event.id


@pytest.mark.asyncio
async def test_two_databases_transaction_paramerror(two_databases):
    with pytest.raises(
        ParamsError,
        match="You are running with multiple databases, so you should specify connection_name",
    ):
        async with in_transaction():
            pass
