import pytest
from pypika_tortoise import CustomFunction

from tests.testmodels import Event, Team, Tournament
from tortoise.contrib import test
from tortoise.contrib.test.condition import In, NotEQ
from tortoise.exceptions import FieldError
from tortoise.expressions import Case, Function, Q, When
from tortoise.functions import Length, Trim


@pytest.mark.asyncio
async def test_values_related_fk(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    event2 = await Event.filter(name="Test").values("name", "tournament__name")
    assert event2[0] == {"name": "Test", "tournament__name": "New Tournament"}


@pytest.mark.asyncio
async def test_values_list_related_fk(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    event2 = await Event.filter(name="Test").values_list("name", "tournament__name")
    assert event2[0] == ("Test", "New Tournament")


@pytest.mark.asyncio
async def test_values_related_rfk(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    tournament2 = await Tournament.filter(name="New Tournament").values("name", "events__name")
    assert tournament2[0] == {"name": "New Tournament", "events__name": "Test"}


@pytest.mark.asyncio
async def test_values_related_rfk_reuse_query(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    query = Tournament.filter(name="New Tournament").values("name", "events__name")
    tournament2 = await query
    assert tournament2[0] == {"name": "New Tournament", "events__name": "Test"}

    tournament2 = await query
    assert tournament2[0] == {"name": "New Tournament", "events__name": "Test"}


@pytest.mark.asyncio
async def test_values_list_related_rfk(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    tournament2 = await Tournament.filter(name="New Tournament").values_list("name", "events__name")
    assert tournament2[0] == ("New Tournament", "Test")


@pytest.mark.asyncio
async def test_values_list_related_rfk_reuse_query(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    query = Tournament.filter(name="New Tournament").values_list("name", "events__name")
    tournament2 = await query
    assert tournament2[0] == ("New Tournament", "Test")

    tournament2 = await query
    assert tournament2[0] == ("New Tournament", "Test")


@pytest.mark.asyncio
async def test_values_related_m2m(db):
    tournament = await Tournament.create(name="New Tournament")
    event = await Event.create(name="Test", tournament_id=tournament.id)
    team = await Team.create(name="Some Team")
    await event.participants.add(team)

    tournament2 = await Event.filter(name="Test").values("name", "participants__name")
    assert tournament2[0] == {"name": "Test", "participants__name": "Some Team"}


@pytest.mark.asyncio
async def test_values_list_related_m2m(db):
    tournament = await Tournament.create(name="New Tournament")
    event = await Event.create(name="Test", tournament_id=tournament.id)
    team = await Team.create(name="Some Team")
    await event.participants.add(team)

    tournament2 = await Event.filter(name="Test").values_list("name", "participants__name")
    assert tournament2[0] == ("Test", "Some Team")


@pytest.mark.asyncio
async def test_values_related_fk_itself(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(ValueError, match='Selecting relation "tournament" is not possible'):
        await Event.filter(name="Test").values("name", "tournament")


@pytest.mark.asyncio
async def test_values_list_related_fk_itself(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(ValueError, match='Selecting relation "tournament" is not possible'):
        await Event.filter(name="Test").values_list("name", "tournament")


@pytest.mark.asyncio
async def test_values_related_rfk_itself(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(ValueError, match='Selecting relation "events" is not possible'):
        await Tournament.filter(name="New Tournament").values("name", "events")


@pytest.mark.asyncio
async def test_values_list_related_rfk_itself(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(ValueError, match='Selecting relation "events" is not possible'):
        await Tournament.filter(name="New Tournament").values_list("name", "events")


@pytest.mark.asyncio
async def test_values_related_m2m_itself(db):
    tournament = await Tournament.create(name="New Tournament")
    event = await Event.create(name="Test", tournament_id=tournament.id)
    team = await Team.create(name="Some Team")
    await event.participants.add(team)

    with pytest.raises(ValueError, match='Selecting relation "participants" is not possible'):
        await Event.filter(name="Test").values("name", "participants")


@pytest.mark.asyncio
async def test_values_list_related_m2m_itself(db):
    tournament = await Tournament.create(name="New Tournament")
    event = await Event.create(name="Test", tournament_id=tournament.id)
    team = await Team.create(name="Some Team")
    await event.participants.add(team)

    with pytest.raises(ValueError, match='Selecting relation "participants" is not possible'):
        await Event.filter(name="Test").values_list("name", "participants")


@pytest.mark.asyncio
async def test_values_bad_key(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(FieldError, match='Unknown field "neem" for model "Event"'):
        await Event.filter(name="Test").values("name", "neem")


@pytest.mark.asyncio
async def test_values_list_bad_key(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(FieldError, match='Unknown field "neem" for model "Event"'):
        await Event.filter(name="Test").values_list("name", "neem")


@pytest.mark.asyncio
async def test_values_related_bad_key(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(FieldError, match='Unknown field "neem" for model "Tournament"'):
        await Event.filter(name="Test").values("name", "tournament__neem")


@pytest.mark.asyncio
async def test_values_list_related_bad_key(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(FieldError, match='Unknown field "neem" for model "Tournament"'):
        await Event.filter(name="Test").values_list("name", "tournament__neem")


@test.requireCapability(dialect="!mssql")
@pytest.mark.asyncio
async def test_values_list_annotations_length(db):
    await Tournament.create(name="Championship")
    await Tournament.create(name="Super Bowl")

    tournaments = await Tournament.annotate(name_length=Length("name")).values_list(
        "name", "name_length"
    )
    assert sorted(tournaments) == sorted([("Championship", 12), ("Super Bowl", 10)])


@test.requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_values_annotations_length(db):
    await Tournament.create(name="Championship")
    await Tournament.create(name="Super Bowl")

    tournaments = await Tournament.annotate(name_slength=Length("name")).values(
        "name", "name_slength"
    )
    assert sorted(tournaments, key=lambda x: x["name"]) == sorted(
        [
            {"name": "Championship", "name_slength": 12},
            {"name": "Super Bowl", "name_slength": 10},
        ],
        key=lambda x: x["name"],
    )


@pytest.mark.asyncio
async def test_values_list_annotations_trim(db):
    await Tournament.create(name="  x")
    await Tournament.create(name=" y ")

    tournaments = await Tournament.annotate(name_trim=Trim("name")).values_list("name", "name_trim")
    assert sorted(tournaments) == sorted([("  x", "x"), (" y ", "y")])


@pytest.mark.asyncio
async def test_values_annotations_trim(db):
    await Tournament.create(name="  x")
    await Tournament.create(name=" y ")

    tournaments = await Tournament.annotate(name_trim=Trim("name")).values("name", "name_trim")
    assert sorted(tournaments, key=lambda x: x["name"]) == sorted(
        [{"name": "  x", "name_trim": "x"}, {"name": " y ", "name_trim": "y"}],
        key=lambda x: x["name"],
    )


@test.requireCapability(dialect=In("sqlite"))
@pytest.mark.asyncio
async def test_values_with_custom_function(db):
    class TruncMonth(Function):
        database_func = CustomFunction("DATE_FORMAT", ["name", "dt_format"])

    sql = Tournament.all().annotate(date=TruncMonth("created", "%Y-%m-%d")).values("date").sql()
    assert sql == 'SELECT DATE_FORMAT("created",?) "date" FROM "tournament"'


@pytest.mark.asyncio
async def test_order_by_annotation_not_in_values(db):
    await Tournament.create(name="2")
    await Tournament.create(name="3")
    await Tournament.create(name="1")

    tournaments = (
        await Tournament.annotate(
            name_orderable=Case(
                When(Q(name="1"), then="a"),
                When(Q(name="2"), then="b"),
                When(Q(name="3"), then="c"),
                default="z",
            )
        )
        .order_by("name_orderable")
        .values("name")
    )
    assert [t["name"] for t in tournaments] == ["1", "2", "3"]


@pytest.mark.asyncio
async def test_order_by_annotation_not_in_values_list(db):
    await Tournament.create(name="2")
    await Tournament.create(name="3")
    await Tournament.create(name="1")

    tournaments = (
        await Tournament.annotate(
            name_orderable=Case(
                When(Q(name="1"), then="a"),
                When(Q(name="2"), then="b"),
                When(Q(name="3"), then="c"),
                default="z",
            )
        )
        .order_by("name_orderable")
        .values_list("name")
    )
    assert tournaments == [("1",), ("2",), ("3",)]
