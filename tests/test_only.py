import pytest
import pytest_asyncio

from tests.testmodels import DoubleFK, Event, SourceFields, StraightFields, Tournament
from tortoise.exceptions import FieldError, IncompleteInstanceError
from tortoise.functions import Count

# ============================================================================
# Fixtures for TestOnlyStraight and TestOnlySource
# ============================================================================


@pytest_asyncio.fixture
async def straight_fields_instance(db):
    """Create a StraightFields instance for testing."""
    return await StraightFields.create(chars="Test")


@pytest_asyncio.fixture
async def source_fields_instance(db):
    """Create a SourceFields instance for testing."""
    return await SourceFields.create(chars="Test")


# ============================================================================
# TestOnlyStraight tests
# ============================================================================


@pytest.mark.asyncio
async def test_only_straight_get(db, straight_fields_instance):
    instance_part = await StraightFields.get(chars="Test").only("chars", "blip")

    assert instance_part.chars == "Test"
    with pytest.raises(AttributeError):
        _ = instance_part.nullable


@pytest.mark.asyncio
async def test_only_straight_filter(db, straight_fields_instance):
    instances = await StraightFields.filter(chars="Test").only("chars", "blip")

    assert len(instances) == 1
    assert instances[0].chars == "Test"
    with pytest.raises(AttributeError):
        _ = instances[0].nullable


@pytest.mark.asyncio
async def test_only_straight_first(db, straight_fields_instance):
    instance_part = await StraightFields.filter(chars="Test").only("chars", "blip").first()

    assert instance_part.chars == "Test"
    with pytest.raises(AttributeError):
        _ = instance_part.nullable


@pytest.mark.asyncio
async def test_only_straight_save(db, straight_fields_instance):
    instance_part = await StraightFields.get(chars="Test").only("chars", "blip")

    with pytest.raises(IncompleteInstanceError, match=" is a partial model"):
        await instance_part.save()


@pytest.mark.asyncio
async def test_only_straight_partial_save(db, straight_fields_instance):
    instance_part = await StraightFields.get(chars="Test").only("chars", "blip")

    with pytest.raises(IncompleteInstanceError, match="Partial update not available"):
        await instance_part.save(update_fields=["chars"])


@pytest.mark.asyncio
async def test_only_straight_partial_save_with_pk_wrong_field(db, straight_fields_instance):
    instance_part = await StraightFields.get(chars="Test").only("chars", "eyedee")

    with pytest.raises(IncompleteInstanceError, match="field 'nullable' is not available"):
        await instance_part.save(update_fields=["nullable"])


@pytest.mark.asyncio
async def test_only_straight_partial_save_with_pk(db, straight_fields_instance):
    instance_part = await StraightFields.get(chars="Test").only("chars", "eyedee")

    instance_part.chars = "Test1"
    await instance_part.save(update_fields=["chars"])

    instance2 = await StraightFields.get(pk=straight_fields_instance.pk)
    assert instance2.chars == "Test1"


# ============================================================================
# TestOnlySource tests (same as Straight but with SourceFields model)
# ============================================================================


@pytest.mark.asyncio
async def test_only_source_get(db, source_fields_instance):
    instance_part = await SourceFields.get(chars="Test").only("chars", "blip")

    assert instance_part.chars == "Test"
    with pytest.raises(AttributeError):
        _ = instance_part.nullable


@pytest.mark.asyncio
async def test_only_source_filter(db, source_fields_instance):
    instances = await SourceFields.filter(chars="Test").only("chars", "blip")

    assert len(instances) == 1
    assert instances[0].chars == "Test"
    with pytest.raises(AttributeError):
        _ = instances[0].nullable


@pytest.mark.asyncio
async def test_only_source_first(db, source_fields_instance):
    instance_part = await SourceFields.filter(chars="Test").only("chars", "blip").first()

    assert instance_part.chars == "Test"
    with pytest.raises(AttributeError):
        _ = instance_part.nullable


@pytest.mark.asyncio
async def test_only_source_save(db, source_fields_instance):
    instance_part = await SourceFields.get(chars="Test").only("chars", "blip")

    with pytest.raises(IncompleteInstanceError, match=" is a partial model"):
        await instance_part.save()


@pytest.mark.asyncio
async def test_only_source_partial_save(db, source_fields_instance):
    instance_part = await SourceFields.get(chars="Test").only("chars", "blip")

    with pytest.raises(IncompleteInstanceError, match="Partial update not available"):
        await instance_part.save(update_fields=["chars"])


@pytest.mark.asyncio
async def test_only_source_partial_save_with_pk_wrong_field(db, source_fields_instance):
    instance_part = await SourceFields.get(chars="Test").only("chars", "eyedee")

    with pytest.raises(IncompleteInstanceError, match="field 'nullable' is not available"):
        await instance_part.save(update_fields=["nullable"])


@pytest.mark.asyncio
async def test_only_source_partial_save_with_pk(db, source_fields_instance):
    instance_part = await SourceFields.get(chars="Test").only("chars", "eyedee")

    instance_part.chars = "Test1"
    await instance_part.save(update_fields=["chars"])

    instance2 = await SourceFields.get(pk=source_fields_instance.pk)
    assert instance2.chars == "Test1"


# ============================================================================
# TestOnlyRecursive tests
# ============================================================================


@pytest.mark.asyncio
async def test_only_recursive_one_level(db):
    left_1st_lvl = await DoubleFK.create(name="1st")
    root = await DoubleFK.create(name="root", left=left_1st_lvl)

    ret = await DoubleFK.filter(pk=root.pk).only("name", "left__name", "left__left__name").first()
    assert ret is not None
    with pytest.raises(AttributeError):
        _ = ret.id
    assert ret.name == "root"
    assert ret.left.name == "1st"
    with pytest.raises(AttributeError):
        _ = ret.left.id
    with pytest.raises(AttributeError):
        _ = ret.right


@pytest.mark.asyncio
async def test_only_recursive_two_levels(db):
    left_2nd_lvl = await DoubleFK.create(name="second leaf")
    left_1st_lvl = await DoubleFK.create(name="1st", left=left_2nd_lvl)
    root = await DoubleFK.create(name="root", left=left_1st_lvl)

    ret = await DoubleFK.filter(pk=root.pk).only("name", "left__name", "left__left__name").first()
    assert ret is not None
    with pytest.raises(AttributeError):
        _ = ret.id
    assert ret.name == "root"
    assert ret.left.name == "1st"
    with pytest.raises(AttributeError):
        _ = ret.left.id
    assert ret.left.left.name == "second leaf"


@pytest.mark.asyncio
async def test_only_recursive_two_levels_reverse_argument_order(db):
    left_2nd_lvl = await DoubleFK.create(name="second leaf")
    left_1st_lvl = await DoubleFK.create(name="1st", left=left_2nd_lvl)
    root = await DoubleFK.create(name="root", left=left_1st_lvl)

    ret = await DoubleFK.filter(pk=root.pk).only("left__left__name", "left__name", "name").first()
    assert ret is not None
    with pytest.raises(AttributeError):
        _ = ret.id
    assert ret.name == "root"
    assert ret.left.name == "1st"
    with pytest.raises(AttributeError):
        _ = ret.left.id
    assert ret.left.left.name == "second leaf"


# ============================================================================
# TestOnlyRelated tests
# ============================================================================


@pytest.mark.asyncio
async def test_only_related_one_level(db):
    tournament = await Tournament.create(name="New Tournament", desc="New Description")
    await Event.create(name="Event 1", tournament=tournament)
    await Event.create(name="Event 2", tournament=tournament)

    ret = (
        await Event.filter(tournament=tournament).only("name", "tournament__name").order_by("name")
    )
    assert len(ret) == 2
    assert ret[0].name == "Event 1"
    with pytest.raises(AttributeError):
        _ = ret[0].alias
    assert ret[1].name == "Event 2"
    with pytest.raises(AttributeError):
        _ = ret[1].alias
    assert ret[0].tournament.name == "New Tournament"
    with pytest.raises(AttributeError):
        _ = ret[0].tournament.id
    with pytest.raises(AttributeError):
        _ = ret[0].tournament.desc


@pytest.mark.asyncio
async def test_only_related_one_level_reversed_argument_order(db):
    tournament = await Tournament.create(name="New Tournament", desc="New Description")
    await Event.create(name="Event 1", tournament=tournament)
    await Event.create(name="Event 2", tournament=tournament)

    ret = (
        await Event.filter(tournament=tournament).only("tournament__name", "name").order_by("name")
    )
    assert len(ret) == 2
    assert ret[0].name == "Event 1"
    assert ret[0].tournament.name == "New Tournament"


@pytest.mark.asyncio
async def test_only_related_just_related(db):
    tournament = await Tournament.create(name="New Tournament", desc="New Description")
    await Event.create(name="Event 1", tournament=tournament)
    await Event.create(name="Event 2", tournament=tournament)

    ret = await Event.filter(tournament=tournament).only("tournament__name").order_by("name").all()
    assert len(ret) == 2
    assert ret[0].tournament.name == "New Tournament"
    assert ret[1].tournament.name == "New Tournament"


# ============================================================================
# Fixture for TestOnlyAdvanced tests
# ============================================================================


@pytest_asyncio.fixture
async def tournament_with_events(db):
    """Create a tournament with two events for advanced tests."""
    tournament = await Tournament.create(name="Tournament A", desc="Description A")
    event1 = await Event.create(name="Event 1", tournament=tournament)
    event2 = await Event.create(name="Event 2", tournament=tournament)
    return tournament, event1, event2


# ============================================================================
# TestOnlyAdvanced tests
# ============================================================================


@pytest.mark.asyncio
async def test_only_advanced_exclude(db, tournament_with_events):
    """Test .only() combined with .exclude()"""
    tournament, event1, event2 = tournament_with_events
    events = await Event.filter(tournament=tournament).exclude(name="Event 2").only("name")
    assert len(events) == 1
    assert events[0].name == "Event 1"
    with pytest.raises(AttributeError):
        _ = events[0].modified


@pytest.mark.asyncio
async def test_only_advanced_limit(db, tournament_with_events):
    """Test .only() combined with .limit()"""
    events = await Event.all().only("name").limit(1)
    assert len(events) == 1
    assert events[0].name == "Event 1"  # Assumes ordering by PK
    with pytest.raises(AttributeError):
        _ = events[0].modified


@pytest.mark.asyncio
async def test_only_advanced_distinct(db, tournament_with_events):
    """Test .only() combined with .distinct()"""
    tournament, event1, event2 = tournament_with_events
    # Create duplicate event names
    await Event.create(name="Event 1", tournament=tournament)

    events = await Event.all().only("name").distinct()
    # Should only have 2 distinct event names
    assert len(events) == 2
    event_names = {e.name for e in events}
    assert event_names == {"Event 1", "Event 2"}


@pytest.mark.asyncio
async def test_only_advanced_values(db, tournament_with_events):
    """Test .only() combined with .values()"""
    with pytest.raises(ValueError):
        await Event.all().only("name").values("name")


@pytest.mark.asyncio
async def test_only_advanced_pk_field(db, tournament_with_events):
    """Test .only() with just the primary key field"""
    tournament = await Tournament.first().only("id")
    assert tournament.id is not None
    with pytest.raises(AttributeError):
        _ = tournament.name


@pytest.mark.asyncio
async def test_only_advanced_empty(db, tournament_with_events):
    """Test .only() with no fields (should raise an error)"""
    with pytest.raises(ValueError):
        await Event.all().only()


@pytest.mark.asyncio
async def test_only_advanced_annotate(db, tournament_with_events):
    tournaments = await Tournament.annotate(event_count=Count("events")).only("name", "event_count")

    assert tournaments[0].name == "Tournament A"
    assert tournaments[0].event_count == 2
    with pytest.raises(AttributeError):
        _ = tournaments[0].desc


@pytest.mark.asyncio
async def test_only_advanced_nonexistent_field(db, tournament_with_events):
    """Test .only() with a field that doesn't exist"""
    with pytest.raises(FieldError):
        await Event.all().only("nonexistent_field").all()


@pytest.mark.asyncio
async def test_only_advanced_join_in_filter(db, tournament_with_events):
    event = await Event.filter(name="Event 1").only("name").first()
    assert event.name == "Event 1"
    with pytest.raises(AttributeError):
        _ = event.tournament

    event = await Event.filter(tournament__name="Tournament A").only("name").first()
    assert event.name == "Event 1"
    with pytest.raises(AttributeError):
        _ = event.tournament

    event = (
        await Event.filter(tournament__name="Tournament A").only("name", "tournament__name").first()
    )
    assert event.name == "Event 1"
    assert event.tournament.name == "Tournament A"


@pytest.mark.asyncio
async def test_only_advanced_join_in_order_by(db, tournament_with_events):
    events = await Event.all().order_by("name").only("name")
    assert events[0].name == "Event 1"
    with pytest.raises(AttributeError):
        _ = events[0].tournament

    events = await Event.all().order_by("tournament__name", "name").only("name")
    assert events[0].name == "Event 1"
    with pytest.raises(AttributeError):
        _ = events[0].tournament

    events = await Event.all().order_by("tournament__name", "name").only("name", "tournament__name")
    assert events[0].name == "Event 1"
    assert events[0].tournament.name == "Tournament A"


@pytest.mark.asyncio
async def test_only_advanced_select_related(db, tournament_with_events):
    """Test .only() with .select_related() for basic functionality"""
    event = (
        await Event.filter(name="Event 1")
        .select_related("tournament")
        .only("name", "tournament__name")
        .first()
    )

    assert event.name == "Event 1"
    assert event.tournament.name == "Tournament A"

    with pytest.raises(AttributeError):
        _ = event.id
    with pytest.raises(AttributeError):
        _ = event.tournament.id
