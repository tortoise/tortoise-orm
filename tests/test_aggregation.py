from decimal import Decimal

import pytest

from tests.testmodels import (
    Author,
    Book,
    Event,
    MinRelation,
    Team,
    Tournament,
    ValidatorModel,
)
from tortoise.contrib import test
from tortoise.contrib.test.condition import In
from tortoise.exceptions import FieldError
from tortoise.expressions import F, Q
from tortoise.functions import Avg, Coalesce, Concat, Count, Lower, Max, Min, Sum, Trim


@pytest.mark.asyncio
async def test_aggregation(db):
    tournament = Tournament(name="New Tournament")
    await tournament.save()
    await Tournament.create(name="Second tournament")
    await Event(name="Without participants", tournament_id=tournament.id).save()
    event = Event(name="Test", tournament_id=tournament.id)
    await event.save()
    participants = []
    for i in range(2):
        team = Team(name=f"Team {(i + 1)}")
        await team.save()
        participants.append(team)
    await event.participants.add(participants[0], participants[1])
    await event.participants.add(participants[0], participants[1])

    tournaments_with_count = (
        await Tournament.all().annotate(events_count=Count("events")).filter(events_count__gte=1)
    )
    assert len(tournaments_with_count) == 1
    assert tournaments_with_count[0].events_count == 2

    event_with_lowest_team_id = (
        await Event.filter(event_id=event.event_id)
        .first()
        .annotate(lowest_team_id=Min("participants__id"))
    )
    assert event_with_lowest_team_id.lowest_team_id == participants[0].id

    ordered_tournaments = (
        await Tournament.all().annotate(events_count=Count("events")).order_by("events_count")
    )
    assert len(ordered_tournaments) == 2
    assert ordered_tournaments[1].id == tournament.id
    event_with_annotation = (
        await Event.all().annotate(tournament_test_id=Sum("tournament__id")).first()
    )
    assert event_with_annotation.tournament_test_id == event_with_annotation.tournament_id

    with pytest.raises(FieldError, match="name__id not resolvable"):
        await Event.all().annotate(tournament_test_id=Sum("name__id")).first()


@pytest.mark.asyncio
async def test_nested_aggregation_in_annotation(db):
    tournament = await Tournament.create(name="0")
    await Tournament.create(name="1")
    event = await Event.create(name="2", tournament=tournament)

    team_first = await Team.create(name="First")
    team_second = await Team.create(name="Second")

    await event.participants.add(team_second)
    await event.participants.add(team_first)

    tournaments = await Tournament.annotate(
        events_participants_count=Count("events__participants")
    ).filter(id=tournament.id)
    assert tournaments[0].events_participants_count == 2


@pytest.mark.asyncio
async def test_aggregation_with_distinct(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Event 1", tournament=tournament)
    await Event.create(name="Event 2", tournament=tournament)
    await MinRelation.create(tournament=tournament)

    tournament_2 = await Tournament.create(name="New Tournament")
    await Event.create(name="Event 1", tournament=tournament_2)
    await Event.create(name="Event 2", tournament=tournament_2)
    await Event.create(name="Event 3", tournament=tournament_2)
    await MinRelation.create(tournament=tournament_2)
    await MinRelation.create(tournament=tournament_2)

    school_with_distinct_count = (
        await Tournament.filter(id=tournament_2.id)
        .annotate(
            events_count=Count("events", distinct=True),
            minrelations_count=Count("minrelations", distinct=True),
        )
        .first()
    )

    assert school_with_distinct_count.events_count == 3
    assert school_with_distinct_count.minrelations_count == 2


@pytest.mark.asyncio
async def test_aggregation_with_filter(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Event 1", tournament=tournament)
    await Event.create(name="Event 2", tournament=tournament)
    await Event.create(name="Event 3", tournament=tournament)

    tournament_with_filter = (
        await Tournament.all()
        .annotate(
            all=Count("events", _filter=Q(name="New Tournament")),
            one=Count("events", _filter=Q(events__name="Event 1")),
            two=Count("events", _filter=Q(events__name__not="Event 1")),
        )
        .first()
    )

    assert tournament_with_filter.all == 3
    assert tournament_with_filter.one == 1
    assert tournament_with_filter.two == 2


@pytest.mark.asyncio
async def test_group_aggregation(db):
    author = await Author.create(name="Some One")
    await Book.create(name="First!", author=author, rating=4)
    await Book.create(name="Second!", author=author, rating=3)
    await Book.create(name="Third!", author=author, rating=3)

    authors = await Author.all().annotate(average_rating=Avg("books__rating"))
    assert authors[0].average_rating == pytest.approx(3.3333333333, rel=1e-5)

    authors = await Author.all().annotate(average_rating=Avg("books__rating")).values()
    assert authors[0]["average_rating"] == pytest.approx(3.3333333333, rel=1e-5)

    authors = (
        await Author.all()
        .annotate(average_rating=Avg("books__rating"))
        .values("id", "name", "average_rating")
    )
    assert authors[0]["average_rating"] == pytest.approx(3.3333333333, rel=1e-5)

    authors = await Author.all().annotate(average_rating=Avg("books__rating")).values_list()
    assert authors[0][2] == pytest.approx(3.3333333333, rel=1e-5)

    authors = (
        await Author.all()
        .annotate(average_rating=Avg("books__rating"))
        .values_list("id", "name", "average_rating")
    )
    assert authors[0][2] == pytest.approx(3.3333333333, rel=1e-5)


@pytest.mark.asyncio
async def test_nested_functions(db):
    author = await Author.create(name="Some One")
    await Book.create(name="First!", author=author, rating=4)
    await Book.create(name="Second!", author=author, rating=3)
    await Book.create(name="Third!", author=author, rating=3)
    ret = await Book.all().annotate(max_name=Lower(Max("name"))).values("max_name")
    assert ret == [{"max_name": "third!"}]


@test.requireCapability(dialect=In("postgres", "mssql"))
@pytest.mark.asyncio
async def test_concat_functions(db):
    author = await Author.create(name="Some One")
    await Book.create(name="Physics Book", author=author, rating=4, subject="physics ")
    await Book.create(name="Mathematics Book", author=author, rating=3, subject=" mathematics")
    await Book.create(name="No-subject Book", author=author, rating=3)
    ret = (
        await Book.all()
        .annotate(long_info=Max(Concat("name", "(", Coalesce(Trim("subject"), "others"), ")")))
        .values("long_info")
    )
    assert ret == [{"long_info": "Physics Book(physics)"}]


@pytest.mark.asyncio
async def test_count_after_aggregate(db):
    author = await Author.create(name="1")
    await Book.create(name="First!", author=author, rating=4)
    await Book.create(name="Second!", author=author, rating=3)
    await Book.create(name="Third!", author=author, rating=3)

    author2 = await Author.create(name="2")
    await Book.create(name="F-2", author=author2, rating=3)
    await Book.create(name="F-3", author=author2, rating=3)

    author3 = await Author.create(name="3")
    await Book.create(name="F-4", author=author3, rating=3)
    await Book.create(name="F-5", author=author3, rating=2)
    ret = (
        await Author.all()
        .annotate(average_rating=Avg("books__rating"))
        .filter(average_rating__gte=3)
        .count()
    )

    assert ret == 2


@pytest.mark.asyncio
async def test_exist_after_aggregate(db):
    author = await Author.create(name="1")
    await Book.create(name="First!", author=author, rating=4)
    await Book.create(name="Second!", author=author, rating=3)
    await Book.create(name="Third!", author=author, rating=3)

    ret = (
        await Author.all()
        .annotate(average_rating=Avg("books__rating"))
        .filter(average_rating__gte=3)
        .exists()
    )

    assert ret is True

    ret = (
        await Author.all()
        .annotate(average_rating=Avg("books__rating"))
        .filter(average_rating__gte=4)
        .exists()
    )
    assert ret is False


@pytest.mark.asyncio
async def test_count_after_aggregate_m2m(db):
    tournament = await Tournament.create(name="1")
    event1 = await Event.create(name="First!", tournament=tournament)
    event2 = await Event.create(name="Second!", tournament=tournament)
    event3 = await Event.create(name="Third!", tournament=tournament)
    event4 = await Event.create(name="Fourth!", tournament=tournament)

    team1 = await Team.create(name="1")
    team2 = await Team.create(name="2")
    team3 = await Team.create(name="3")

    await event1.participants.add(team1, team2, team3)
    await event2.participants.add(team1, team2)
    await event3.participants.add(team1)
    await event4.participants.add(team1, team2, team3)

    query = (
        Event.filter(participants__id__in=[team1.id, team2.id, team3.id])
        .annotate(count=Count("event_id"))
        .filter(count=3)
        .prefetch_related("participants")
    )
    result = await query
    assert len(result) == 2

    res = await query.count()
    assert res == 2


@pytest.mark.asyncio
async def test_where_and_having(db):
    author = await Author.create(name="1")
    await Book.create(name="First!", author=author, rating=4)
    await Book.create(name="Second!", author=author, rating=3)
    await Book.create(name="Third!", author=author, rating=3)

    query = Book.exclude(name="First!").annotate(avg_rating=Avg("rating")).values("avg_rating")
    result = await query
    assert len(result) == 1
    assert result[0]["avg_rating"] == 3


@pytest.mark.asyncio
async def test_count_without_matching(db) -> None:
    await Tournament.create(name="Test")

    query = Tournament.annotate(events_count=Count("events")).filter(events_count__gt=0).count()
    result = await query
    assert result == 0


@pytest.mark.asyncio
async def test_int_sum_on_models_with_validators(db) -> None:
    await ValidatorModel.create(max_value=2)
    await ValidatorModel.create(max_value=2)

    query = ValidatorModel.annotate(sum=Sum("max_value")).values("sum")
    result = await query
    assert result == [{"sum": 4}]


@pytest.mark.asyncio
async def test_int_sum_math_on_models_with_validators(db) -> None:
    await ValidatorModel.create(max_value=4)
    await ValidatorModel.create(max_value=4)

    query = ValidatorModel.annotate(sum=Sum(F("max_value") * F("max_value"))).values("sum")
    result = await query
    assert result == [{"sum": 32}]


@pytest.mark.asyncio
async def test_decimal_sum_on_models_with_validators(db) -> None:
    await ValidatorModel.create(min_value_decimal=2.0)

    query = ValidatorModel.annotate(sum=Sum("min_value_decimal")).values("sum")
    result = await query
    assert result == [{"sum": Decimal("2.0")}]


@pytest.mark.asyncio
async def test_decimal_sum_with_math_on_models_with_validators(db) -> None:
    await ValidatorModel.create(min_value_decimal=2.0)

    query = ValidatorModel.annotate(
        sum=Sum(F("min_value_decimal") - F("min_value_decimal") * F("min_value_decimal"))
    ).values("sum")
    result = await query
    assert result == [{"sum": Decimal("-2.0")}]


@pytest.mark.asyncio
async def test_function_requiring_nested_joins(db):
    tournament = await Tournament.create(name="Tournament")

    event_first = await Event.create(name="1", tournament=tournament)
    event_second = await Event.create(name="2", tournament=tournament)

    team_first = await Team.create(name="First", alias=2)
    team_second = await Team.create(name="Second", alias=10)

    await team_first.events.add(event_first)
    await event_second.participants.add(team_second)

    res = await Tournament.annotate(avg=Avg("events__participants__alias")).values("avg")
    assert res == [{"avg": 6}]
