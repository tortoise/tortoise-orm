import pytest

from tests.testmodels import Event, Tournament
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ
from tortoise.expressions import F
from tortoise.functions import Length


@pytest.mark.asyncio
async def test_annotations(db):
    a = await Tournament.create(name="A")

    base_query = Tournament.annotate(id_plus_one=F("id") + 1)
    query1 = base_query.annotate(id_plus_two=F("id") + 2)
    query2 = base_query.annotate(id_plus_three=F("id") + 3)
    res = await query1.first()
    assert res.id_plus_one == a.id + 1
    assert res.id_plus_two == a.id + 2
    with pytest.raises(AttributeError):
        getattr(res, "id_plus_three")

    res = await query2.first()
    assert res.id_plus_one == a.id + 1
    assert res.id_plus_three == a.id + 3
    with pytest.raises(AttributeError):
        getattr(res, "id_plus_two")

    res = await query1.first()
    with pytest.raises(AttributeError):
        getattr(res, "id_plus_three")


@pytest.mark.asyncio
async def test_filters(db):
    a = await Tournament.create(name="A")
    b = await Tournament.create(name="B")
    await Tournament.create(name="C")

    base_query = Tournament.exclude(name="C")
    tournaments = await base_query
    assert set(tournaments) == {a, b}

    tournaments = await base_query.exclude(name="A")
    assert set(tournaments) == {b}

    tournaments = await base_query.exclude(name="B")
    assert set(tournaments) == {a}


@pytest.mark.asyncio
async def test_joins(db):
    tournament_a = await Tournament.create(name="A")
    tournament_b = await Tournament.create(name="B")
    tournament_c = await Tournament.create(name="C")
    event_a = await Event.create(name="A", tournament=tournament_a)
    event_b = await Event.create(name="B", tournament=tournament_b)
    await Event.create(name="C", tournament=tournament_c)

    base_query = Event.exclude(tournament__name="C")
    events = await base_query
    assert set(events) == {event_a, event_b}

    events = await base_query.exclude(name="A")
    assert set(events) == {event_b}

    events = await base_query.exclude(name="B")
    assert set(events) == {event_a}


@pytest.mark.asyncio
async def test_order_by(db):
    a = await Tournament.create(name="A")
    b = await Tournament.create(name="B")

    base_query = Tournament.all().order_by("name")
    tournaments = await base_query
    assert tournaments == [a, b]

    tournaments = await base_query.order_by("-name")
    assert tournaments == [b, a]


@test.requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_values_with_annotations(db):
    await Tournament.create(name="Championship")
    await Tournament.create(name="Super Bowl")

    base_query = Tournament.annotate(name_length=Length("name"))
    tournaments = await base_query.values_list("name")
    assert sorted(tournaments) == sorted([("Championship",), ("Super Bowl",)])

    tournaments = await base_query.values_list("name_length")
    assert sorted(tournaments) == sorted([(10,), (12,)])
