import pytest

from tests.testmodels import (
    DefaultOrdered,
    DefaultOrderedDesc,
    DefaultOrderedInvalid,
    Event,
    FKToDefaultOrdered,
    Tournament,
)
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ
from tortoise.exceptions import ConfigurationError, FieldError
from tortoise.expressions import Case, Q, When
from tortoise.functions import Count, Lower, Sum

# ============================================================================
# TestOrderBy tests
# ============================================================================


@pytest.mark.asyncio
async def test_order_by(db):
    await Tournament.create(name="1")
    await Tournament.create(name="2")

    tournaments = await Tournament.all().order_by("name")
    assert [t.name for t in tournaments] == ["1", "2"]


@pytest.mark.asyncio
async def test_order_by_reversed(db):
    await Tournament.create(name="1")
    await Tournament.create(name="2")

    tournaments = await Tournament.all().order_by("-name")
    assert [t.name for t in tournaments] == ["2", "1"]


@pytest.mark.asyncio
async def test_order_by_related(db):
    tournament_first = await Tournament.create(name="1")
    tournament_second = await Tournament.create(name="2")
    await Event.create(name="b", tournament=tournament_first)
    await Event.create(name="a", tournament=tournament_second)

    tournaments = await Tournament.all().order_by("events__name")
    assert [t.name for t in tournaments] == ["2", "1"]


@pytest.mark.asyncio
async def test_order_by_ambigious_field_name(db):
    tournament_first = await Tournament.create(name="Tournament 1", desc="d1")
    tournament_second = await Tournament.create(name="Tournament 2", desc="d2")

    event_third = await Event.create(name="3", tournament=tournament_second)
    event_second = await Event.create(name="2", tournament=tournament_first)
    event_first = await Event.create(name="1", tournament=tournament_first)

    res = await Event.all().order_by("tournament__name", "name")
    assert res == [event_first, event_second, event_third]


@pytest.mark.asyncio
async def test_order_by_related_reversed(db):
    tournament_first = await Tournament.create(name="1")
    tournament_second = await Tournament.create(name="2")
    await Event.create(name="b", tournament=tournament_first)
    await Event.create(name="a", tournament=tournament_second)

    tournaments = await Tournament.all().order_by("-events__name")
    assert [t.name for t in tournaments] == ["1", "2"]


@pytest.mark.asyncio
async def test_order_by_relation(db):
    with pytest.raises(FieldError):
        tournament_first = await Tournament.create(name="1")
        await Event.create(name="b", tournament=tournament_first)

        await Tournament.all().order_by("events")


@pytest.mark.asyncio
async def test_order_by_unknown_field(db):
    with pytest.raises(FieldError):
        tournament_first = await Tournament.create(name="1")
        await Event.create(name="b", tournament=tournament_first)

        await Tournament.all().order_by("something_else")


@pytest.mark.asyncio
async def test_order_by_aggregation(db):
    tournament_first = await Tournament.create(name="1")
    tournament_second = await Tournament.create(name="2")
    await Event.create(name="b", tournament=tournament_first)
    await Event.create(name="c", tournament=tournament_first)
    await Event.create(name="a", tournament=tournament_second)

    tournaments = await Tournament.annotate(events_count=Count("events")).order_by("events_count")
    assert [t.name for t in tournaments] == ["2", "1"]


@pytest.mark.asyncio
async def test_order_by_aggregation_reversed(db):
    tournament_first = await Tournament.create(name="1")
    tournament_second = await Tournament.create(name="2")
    await Event.create(name="b", tournament=tournament_first)
    await Event.create(name="c", tournament=tournament_first)
    await Event.create(name="a", tournament=tournament_second)

    tournaments = await Tournament.annotate(events_count=Count("events")).order_by("-events_count")
    assert [t.name for t in tournaments] == ["1", "2"]


@pytest.mark.asyncio
async def test_order_by_reserved_word_annotation(db):
    await Tournament.create(name="1")
    await Tournament.create(name="2")

    reserved_words = ["order", "group", "limit", "offset", "where"]

    for word in reserved_words:
        tournaments = await Tournament.annotate(**{word: Lower("name")}).order_by(word)
        assert [t.name for t in tournaments] == ["1", "2"]


@pytest.mark.asyncio
async def test_distinct_values_with_annotation(db):
    await Tournament.create(name="3")
    await Tournament.create(name="1")
    await Tournament.create(name="2")

    tournaments = (
        await Tournament.annotate(
            name_orderable=Case(
                When(Q(name="1"), then="1"),
                When(Q(name="2"), then="2"),
                When(Q(name="3"), then="3"),
                default="-1",
            ),
        )
        .distinct()
        .order_by("name_orderable", "-created")
        .values("name", "name_orderable", "created")
    )
    assert [t["name"] for t in tournaments] == ["1", "2", "3"]


@pytest.mark.asyncio
async def test_distinct_all_with_annotation(db):
    await Tournament.create(name="3")
    await Tournament.create(name="1")
    await Tournament.create(name="2")

    tournaments = (
        await Tournament.annotate(
            name_orderable=Case(
                When(Q(name="1"), then="1"),
                When(Q(name="2"), then="2"),
                When(Q(name="3"), then="3"),
                default="-1",
            ),
        )
        .distinct()
        .order_by("name_orderable", "-created")
    )
    assert [t.name for t in tournaments] == ["1", "2", "3"]


# ============================================================================
# TestDefaultOrdering tests
# ============================================================================


@pytest.mark.asyncio
@test.requireCapability(dialect=NotEQ("oracle"))
async def test_default_order(db):
    await DefaultOrdered.create(one="2", second=1)
    await DefaultOrdered.create(one="1", second=1)

    instance_list = await DefaultOrdered.all()
    assert [i.one for i in instance_list] == ["1", "2"]


@pytest.mark.asyncio
@test.requireCapability(dialect=NotEQ("oracle"))
async def test_default_order_desc(db):
    await DefaultOrderedDesc.create(one="1", second=1)
    await DefaultOrderedDesc.create(one="2", second=1)

    instance_list = await DefaultOrderedDesc.all()
    assert [i.one for i in instance_list] == ["2", "1"]


@pytest.mark.asyncio
async def test_default_order_invalid(db):
    await DefaultOrderedInvalid.create(one="1", second=1)
    await DefaultOrderedInvalid.create(one="2", second=1)

    with pytest.raises(ConfigurationError):
        await DefaultOrderedInvalid.all()


@pytest.mark.asyncio
async def test_default_order_annotated_query(db):
    instance = await DefaultOrdered.create(one="2", second=1)
    await FKToDefaultOrdered.create(link=instance, value=10)
    await DefaultOrdered.create(one="1", second=1)

    queryset = DefaultOrdered.all().annotate(res=Sum("related__value"))
    queryset._make_query()
    query = queryset.query.get_sql()
    assert "order by" not in query.lower()
