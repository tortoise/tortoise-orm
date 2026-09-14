import pytest

from tests import testmodels
from tortoise.exceptions import (
    IntegrityError,
    NoValuesFetched,
    OperationalError,
    ValidationError,
)
from tortoise.queryset import QuerySet


def assert_raises_wrong_type_exception(relation_name: str):
    """Context manager that asserts ValidationError with wrong type message."""
    return pytest.raises(
        ValidationError, match=f"Invalid type for relationship field '{relation_name}'"
    )


@pytest.mark.asyncio
async def test_empty(db):
    with pytest.raises(IntegrityError):
        await testmodels.MinRelation.create()


@pytest.mark.asyncio
async def test_minimal__create_by_id(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament_id=tour.id)
    assert rel.tournament_id == tour.id
    assert (await tour.minrelations.all())[0] == rel


@pytest.mark.asyncio
async def test_minimal__create_by_name(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    await rel.fetch_related("tournament")
    assert rel.tournament == tour
    assert (await tour.minrelations.all())[0] == rel


@pytest.mark.asyncio
async def test_minimal__by_name__created_prefetched(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    assert rel.tournament == tour
    assert (await tour.minrelations.all())[0] == rel


@pytest.mark.asyncio
async def test_minimal__by_name__unfetched(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    rel = await testmodels.MinRelation.get(id=rel.id)
    assert isinstance(rel.tournament, QuerySet)


@pytest.mark.asyncio
async def test_minimal__by_name__re_awaited(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    await rel.fetch_related("tournament")
    assert rel.tournament == tour
    assert await rel.tournament == tour


@pytest.mark.asyncio
async def test_minimal__by_name__awaited(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    rel = await testmodels.MinRelation.get(id=rel.id)
    assert await rel.tournament == tour
    assert (await tour.minrelations.all())[0] == rel


@pytest.mark.asyncio
async def test_event__create_by_id(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.Event.create(name="Event1", tournament_id=tour.id)
    assert rel.tournament_id == tour.id
    assert (await tour.events.all())[0] == rel


@pytest.mark.asyncio
async def test_event__create_by_name(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.Event.create(name="Event1", tournament=tour)
    await rel.fetch_related("tournament")
    assert rel.tournament == tour
    assert (await tour.events.all())[0] == rel


@pytest.mark.asyncio
async def test_update_by_name(db):
    tour = await testmodels.Tournament.create(name="Team1")
    tour2 = await testmodels.Tournament.create(name="Team2")
    rel0 = await testmodels.Event.create(name="Event1", tournament=tour)

    await testmodels.Event.filter(pk=rel0.pk).update(tournament=tour2)
    rel = await testmodels.Event.get(event_id=rel0.event_id)

    await rel.fetch_related("tournament")
    assert rel.tournament == tour2
    assert await tour.events.all() == []
    assert (await tour2.events.all())[0] == rel


@pytest.mark.asyncio
async def test_update_by_id(db):
    tour = await testmodels.Tournament.create(name="Team1")
    tour2 = await testmodels.Tournament.create(name="Team2")
    rel0 = await testmodels.Event.create(name="Event1", tournament_id=tour.id)

    await testmodels.Event.filter(event_id=rel0.event_id).update(tournament_id=tour2.id)
    rel = await testmodels.Event.get(pk=rel0.pk)

    assert rel.tournament_id == tour2.id
    assert await tour.events.all() == []
    assert (await tour2.events.all())[0] == rel


@pytest.mark.asyncio
async def test_minimal__uninstantiated_create(db):
    tour = testmodels.Tournament(name="Team1")
    with pytest.raises(OperationalError, match="You should first call .save()"):
        await testmodels.MinRelation.create(tournament=tour)


@pytest.mark.asyncio
async def test_minimal__uninstantiated_iterate(db):
    tour = testmodels.Tournament(name="Team1")
    with pytest.raises(OperationalError, match="This objects hasn't been instanced, call .save()"):
        async for _ in tour.minrelations:
            pass


@pytest.mark.asyncio
async def test_minimal__uninstantiated_await(db):
    tour = testmodels.Tournament(name="Team1")
    with pytest.raises(OperationalError, match="This objects hasn't been instanced, call .save()"):
        await tour.minrelations


@pytest.mark.asyncio
async def test_minimal__unfetched_contains(db):
    tour = await testmodels.Tournament.create(name="Team1")
    with pytest.raises(
        NoValuesFetched,
        match="No values were fetched for this relation, first use .fetch_related()",
    ):
        "a" in tour.minrelations  # pylint: disable=W0104


@pytest.mark.asyncio
async def test_minimal__unfetched_iter(db):
    tour = await testmodels.Tournament.create(name="Team1")
    with pytest.raises(
        NoValuesFetched,
        match="No values were fetched for this relation, first use .fetch_related()",
    ):
        for _ in tour.minrelations:
            pass


@pytest.mark.asyncio
async def test_minimal__unfetched_len(db):
    tour = await testmodels.Tournament.create(name="Team1")
    with pytest.raises(
        NoValuesFetched,
        match="No values were fetched for this relation, first use .fetch_related()",
    ):
        len(tour.minrelations)


@pytest.mark.asyncio
async def test_minimal__unfetched_bool(db):
    tour = await testmodels.Tournament.create(name="Team1")
    with pytest.raises(
        NoValuesFetched,
        match="No values were fetched for this relation, first use .fetch_related()",
    ):
        bool(tour.minrelations)


@pytest.mark.asyncio
async def test_minimal__unfetched_getitem(db):
    tour = await testmodels.Tournament.create(name="Team1")
    with pytest.raises(
        NoValuesFetched,
        match="No values were fetched for this relation, first use .fetch_related()",
    ):
        tour.minrelations[0]  # pylint: disable=W0104


@pytest.mark.asyncio
async def test_minimal__instantiated_create(db):
    tour = await testmodels.Tournament.create(name="Team1")
    await testmodels.MinRelation.create(tournament=tour)


@pytest.mark.asyncio
async def test_minimal__instantiated_create_wrong_type(db):
    author = await testmodels.Author.create(name="Author1")
    with assert_raises_wrong_type_exception("tournament"):
        await testmodels.MinRelation.create(tournament=author)


@pytest.mark.asyncio
async def test_minimal__instantiated_iterate(db):
    tour = await testmodels.Tournament.create(name="Team1")
    async for _ in tour.minrelations:
        pass


@pytest.mark.asyncio
async def test_minimal__instantiated_await(db):
    tour = await testmodels.Tournament.create(name="Team1")
    await tour.minrelations


@pytest.mark.asyncio
async def test_minimal__fetched_contains(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    await tour.fetch_related("minrelations")
    assert rel in tour.minrelations


@pytest.mark.asyncio
async def test_minimal__fetched_iter(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    await tour.fetch_related("minrelations")
    assert list(tour.minrelations) == [rel]


@pytest.mark.asyncio
async def test_minimal__fetched_len(db):
    tour = await testmodels.Tournament.create(name="Team1")
    await testmodels.MinRelation.create(tournament=tour)
    await tour.fetch_related("minrelations")
    assert len(tour.minrelations) == 1


@pytest.mark.asyncio
async def test_minimal__fetched_bool(db):
    tour = await testmodels.Tournament.create(name="Team1")
    await tour.fetch_related("minrelations")
    assert not bool(tour.minrelations)
    await testmodels.MinRelation.create(tournament=tour)
    await tour.fetch_related("minrelations")
    assert bool(tour.minrelations)


@pytest.mark.asyncio
async def test_minimal__fetched_getitem(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    await tour.fetch_related("minrelations")
    assert tour.minrelations[0] == rel

    with pytest.raises(IndexError):
        tour.minrelations[1]  # pylint: disable=W0104


@pytest.mark.asyncio
async def test_event__filter(db):
    tour = await testmodels.Tournament.create(name="Team1")
    event1 = await testmodels.Event.create(name="Event1", tournament=tour)
    event2 = await testmodels.Event.create(name="Event2", tournament=tour)
    assert await tour.events.filter(name="Event1") == [event1]
    assert await tour.events.filter(name="Event2") == [event2]
    assert await tour.events.filter(name="Event3") == []


@pytest.mark.asyncio
async def test_event__all(db):
    tour = await testmodels.Tournament.create(name="Team1")
    event1 = await testmodels.Event.create(name="Event1", tournament=tour)
    event2 = await testmodels.Event.create(name="Event2", tournament=tour)
    assert set(await tour.events.all()) == {event1, event2}


@pytest.mark.asyncio
async def test_event__order_by(db):
    tour = await testmodels.Tournament.create(name="Team1")
    event1 = await testmodels.Event.create(name="Event1", tournament=tour)
    event2 = await testmodels.Event.create(name="Event2", tournament=tour)
    assert await tour.events.order_by("-name") == [event2, event1]
    assert await tour.events.order_by("name") == [event1, event2]


@pytest.mark.asyncio
async def test_event__limit(db):
    tour = await testmodels.Tournament.create(name="Team1")
    event1 = await testmodels.Event.create(name="Event1", tournament=tour)
    event2 = await testmodels.Event.create(name="Event2", tournament=tour)
    await testmodels.Event.create(name="Event3", tournament=tour)
    assert await tour.events.limit(2).order_by("name") == [event1, event2]


@pytest.mark.asyncio
async def test_event__offset(db):
    tour = await testmodels.Tournament.create(name="Team1")
    await testmodels.Event.create(name="Event1", tournament=tour)
    event2 = await testmodels.Event.create(name="Event2", tournament=tour)
    event3 = await testmodels.Event.create(name="Event3", tournament=tour)
    assert await tour.events.offset(1).order_by("name") == [event2, event3]


@pytest.mark.asyncio
async def test_fk_correct_type_assignment(db):
    tour1 = await testmodels.Tournament.create(name="Team1")
    tour2 = await testmodels.Tournament.create(name="Team2")
    event = await testmodels.Event(name="Event1", tournament=tour1)

    event.tournament = tour2
    await event.save()
    assert event.tournament_id == tour2.id


@pytest.mark.asyncio
async def test_fk_wrong_type_assignment(db):
    tour = await testmodels.Tournament.create(name="Team1")
    author = await testmodels.Author.create(name="Author")
    rel = await testmodels.MinRelation.create(tournament=tour)

    with assert_raises_wrong_type_exception("tournament"):
        rel.tournament = author


@pytest.mark.asyncio
async def test_fk_none_assignment(db):
    manager = await testmodels.Employee.create(name="Manager")
    employee = await testmodels.Employee.create(name="Employee", manager=manager)

    employee.manager = None
    await employee.save()
    assert employee.manager is None


@pytest.mark.asyncio
async def test_fk_update_wrong_type(db):
    tour = await testmodels.Tournament.create(name="Team1")
    rel = await testmodels.MinRelation.create(tournament=tour)
    author = await testmodels.Author.create(name="Author1")

    with assert_raises_wrong_type_exception("tournament"):
        await testmodels.MinRelation.filter(id=rel.id).update(tournament=author)


@pytest.mark.asyncio
async def test_fk_bulk_create_wrong_type(db):
    author = await testmodels.Author.create(name="Author")
    with assert_raises_wrong_type_exception("tournament"):
        await testmodels.MinRelation.bulk_create(
            [testmodels.MinRelation(tournament=author) for _ in range(10)]
        )


@pytest.mark.asyncio
async def test_fk_bulk_update_wrong_type(db):
    tour = await testmodels.Tournament.create(name="Team1")
    await testmodels.MinRelation.bulk_create(
        [testmodels.MinRelation(tournament=tour) for _ in range(1, 10)]
    )
    author = await testmodels.Author.create(name="Author")

    with assert_raises_wrong_type_exception("tournament"):
        relations = await testmodels.MinRelation.all()
        await testmodels.MinRelation.bulk_update(
            [testmodels.MinRelation(id=rel.id, tournament=author) for rel in relations],
            fields=["tournament"],
        )


# ============================================================================
# deconstruct() keeps the declared source_field (#2283)
# ============================================================================


@pytest.mark.asyncio
async def test_deconstruct_fk_keeps_declared_source_field(db):
    # After the relations are initialised, fk.source_field holds the name of the
    # generated `<field>_id` backing field, not the column name. deconstruct() must
    # still report the column the user declared, or makemigrations writes the wrong
    # column name and a migrated schema disagrees with generate_schemas().
    fk = testmodels.SourceFields._meta.fields_map["fk"]
    assert fk.source_field == "fk_id"
    _, _, kwargs = fk.deconstruct()
    assert kwargs["source_field"] == "fk_sometable"


@pytest.mark.asyncio
async def test_deconstruct_o2o_keeps_declared_source_field(db):
    o2o = testmodels.SourceFields._meta.fields_map["o2o"]
    assert o2o.source_field == "o2o_id"
    _, _, kwargs = o2o.deconstruct()
    assert kwargs["source_field"] == "o2o_sometable"


@pytest.mark.asyncio
async def test_deconstruct_fk_without_source_field_uses_default_column(db):
    # A field that declared no source_field keeps the `<field>_id` default.
    fk = testmodels.Event._meta.fields_map["tournament"]
    _, _, kwargs = fk.deconstruct()
    assert kwargs["source_field"] == "tournament_id"


@pytest.mark.asyncio
async def test_deconstruct_source_field_matches_db_column(db):
    # The deconstructed value must be the column the schema generator actually creates.
    for model, field_name in (
        (testmodels.SourceFields, "fk"),
        (testmodels.SourceFields, "o2o"),
        (testmodels.Event, "tournament"),
    ):
        field = model._meta.fields_map[field_name]
        _, _, kwargs = field.deconstruct()
        backing = model._meta.fields_map[field.source_field]
        assert kwargs["source_field"] == backing.source_field
        assert kwargs["source_field"] in model._meta.db_fields
