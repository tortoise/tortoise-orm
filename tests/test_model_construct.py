"""
Tests for Model.construct() classmethod.

This method creates model instances without validation, DB checks, or FK restrictions.
All tests use the ``db`` fixture to ensure Tortoise is initialized and _meta is fully populated.
"""

import pytest

from tests.testmodels import (
    Author,
    Book,
    Dest_null,
    Event,
    O2O_null,
    Reporter,
    Team,
    Tournament,
)
from tortoise.fields.relational import ManyToManyRelation, ReverseRelation

# ---------------------------------------------------------------------------
# Basic data field construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_simple_fields(db):
    instance = Tournament.construct(id=1, name="Test")
    assert instance.id == 1
    assert instance.name == "Test"
    assert instance._saved_in_db is False


@pytest.mark.asyncio
async def test_construct_saved_in_db_flag(db):
    instance = Tournament.construct(id=1, name="Test", _saved_in_db=True)
    assert instance._saved_in_db is True


@pytest.mark.asyncio
async def test_construct_defaults_applied(db):
    instance = Tournament.construct(name="Test")
    # id was not provided so should default to None
    assert instance.id is None


@pytest.mark.asyncio
async def test_construct_partial_and_custom_pk_flags(db):
    instance = Tournament.construct(id=1, name="Test")
    assert instance._partial is False
    assert instance._custom_generated_pk is False


# ---------------------------------------------------------------------------
# Forward FK field construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_with_fk_object(db):
    tournament = Tournament.construct(id=1, name="T")
    event = Event.construct(name="E", tournament=tournament)
    assert event.tournament is tournament
    assert event.tournament.name == "T"
    assert event.tournament_id == 1


@pytest.mark.asyncio
async def test_construct_with_fk_none(db):
    event = Event.construct(name="E", tournament=None)
    assert event.tournament_id is None


@pytest.mark.asyncio
async def test_construct_with_fk_unsaved_allowed(db):
    """Unlike __init__, construct() does NOT check _saved_in_db on FK values."""
    tournament = Tournament.construct(name="T")
    # This should NOT raise even though tournament is not saved
    event = Event.construct(name="E", tournament=tournament)
    assert event.tournament is tournament


@pytest.mark.asyncio
async def test_construct_with_source_field_directly(db):
    event = Event.construct(name="E", tournament_id=42)
    assert event.tournament_id == 42


# ---------------------------------------------------------------------------
# Reverse FK (backward FK) field construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_backward_fk_as_list(db):
    e1 = Event.construct(name="E1")
    e2 = Event.construct(name="E2")
    tournament = Tournament.construct(id=1, name="T", events=[e1, e2])
    assert len(tournament.events) == 2
    assert [e.name for e in tournament.events] == ["E1", "E2"]


@pytest.mark.asyncio
async def test_construct_backward_fk_is_reverse_relation(db):
    tournament = Tournament.construct(id=1, name="T", events=[Event.construct(name="E")])
    assert isinstance(tournament.events, ReverseRelation)


@pytest.mark.asyncio
async def test_construct_backward_fk_fetched(db):
    tournament = Tournament.construct(id=1, name="T", events=[])
    assert tournament.events._fetched is True


@pytest.mark.asyncio
async def test_construct_backward_fk_empty_list(db):
    tournament = Tournament.construct(id=1, name="T", events=[])
    assert len(tournament.events) == 0
    assert bool(tournament.events) is False


@pytest.mark.asyncio
async def test_construct_backward_fk_contains(db):
    event = Event.construct(name="E1")
    tournament = Tournament.construct(id=1, name="T", events=[event])
    assert event in tournament.events


# ---------------------------------------------------------------------------
# M2M field construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_m2m_as_list(db):
    t1 = Team.construct(id=1, name="T1")
    t2 = Team.construct(id=2, name="T2")
    event = Event.construct(name="E", participants=[t1, t2])
    assert len(event.participants) == 2
    assert [t.name for t in event.participants] == ["T1", "T2"]


@pytest.mark.asyncio
async def test_construct_m2m_is_m2m_relation(db):
    event = Event.construct(name="E", participants=[Team.construct(name="T")])
    assert isinstance(event.participants, ManyToManyRelation)


@pytest.mark.asyncio
async def test_construct_m2m_fetched(db):
    event = Event.construct(name="E", participants=[])
    assert event.participants._fetched is True


@pytest.mark.asyncio
async def test_construct_m2m_empty_list(db):
    event = Event.construct(name="E", participants=[])
    assert len(event.participants) == 0


# ---------------------------------------------------------------------------
# Backward O2O field construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_backward_o2o(db):
    """Dest_null has backward O2O 'address_null' from O2O_null."""
    o2o_instance = O2O_null.construct(name="test_o2o")
    dest = Dest_null.construct(name="dest", address_null=o2o_instance)
    assert dest.address_null is o2o_instance
    assert dest.address_null.name == "test_o2o"


# ---------------------------------------------------------------------------
# Forward O2O field construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_forward_o2o(db):
    """Address has a forward O2O field 'event' pointing to Event."""
    from tests.testmodels import Address

    event = Event.construct(event_id=10, name="E")
    address = Address.construct(city="NYC", street="5th Ave", event=event)
    assert address.event is event
    assert address.event_id == 10


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_callable_default(db):
    """Event has token field with default=generate_token (callable)."""
    event = Event.construct(name="E")
    assert event.token is not None
    assert isinstance(event.token, str)
    assert len(event.token) > 0


@pytest.mark.asyncio
async def test_construct_none_default(db):
    """Fields without explicit defaults should get None."""
    event = Event.construct(name="E")
    # alias is IntField(null=True) with no explicit default
    assert event.alias is None


@pytest.mark.asyncio
async def test_construct_unprovided_relation_fields_no_default(db):
    """Backward FK/M2M fields not provided should not raise errors.
    They are lazily created by the property getter."""
    tournament = Tournament.construct(name="T")
    # Accessing the events reverse FK should create a lazy ReverseRelation
    events = tournament.events
    assert isinstance(events, ReverseRelation)


# ---------------------------------------------------------------------------
# No validation enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_no_null_validation(db):
    """Unlike __init__, construct() should NOT raise ValueError for null in non-nullable fields."""
    # Event.name is a non-nullable TextField
    event = Event.construct(name=None)
    assert event.name is None


@pytest.mark.asyncio
async def test_construct_no_fk_saved_check(db):
    """construct() should accept unsaved FK objects without raising."""
    tournament = Tournament.construct(name="Unsaved")
    assert tournament._saved_in_db is False
    event = Event.construct(name="E", tournament=tournament)
    assert event.tournament is tournament


# ---------------------------------------------------------------------------
# Without Tortoise initialization (no db fixture)
# ---------------------------------------------------------------------------


def test_construct_simple_fields_without_init():
    """Simple data fields should work without Tortoise.init() / db fixture."""
    instance = Tournament.construct(id=1, name="Test")
    assert instance.id == 1
    assert instance.name == "Test"
    assert instance._saved_in_db is False
    assert instance.pk == 1
    assert repr(instance) == "<Tournament: 1>"
    assert str(instance) == "Test"


def test_construct_unknown_kwargs_without_init():
    """Unknown kwargs should work without initialization."""
    instance = Tournament.construct(name="T", custom_attr="hello")
    assert instance.custom_attr == "hello"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_pk_accessible(db):
    assert Tournament.construct(id=5, name="T").pk == 5


@pytest.mark.asyncio
async def test_construct_repr(db):
    instance = Tournament.construct(id=5, name="T")
    assert repr(instance) == "<Tournament: 5>"


@pytest.mark.asyncio
async def test_construct_str(db):
    instance = Tournament.construct(name="MyTournament")
    assert str(instance) == "MyTournament"


@pytest.mark.asyncio
async def test_construct_unknown_kwargs_stored(db):
    """Unknown kwargs should be stored as instance attributes (no validation)."""
    instance = Tournament.construct(name="T", nonexistent=42)
    assert instance.nonexistent == 42


@pytest.mark.asyncio
async def test_construct_fk_source_field_not_overwritten_by_defaults(db):
    """When tournament=obj is passed, tournament_id should not be overwritten to None by defaults."""
    tournament = Tournament.construct(id=7, name="T")
    event = Event.construct(name="E", tournament=tournament)
    assert event.tournament_id == 7


@pytest.mark.asyncio
async def test_construct_nullable_fk(db):
    """Nullable FK field set to None should work."""
    event = Event.construct(name="E", reporter=None)
    assert event.reporter_id is None


@pytest.mark.asyncio
async def test_construct_nullable_fk_with_object(db):
    """Nullable FK field set to an object should work."""
    reporter = Reporter.construct(id=1, name="R")
    event = Event.construct(name="E", reporter=reporter)
    assert event.reporter is reporter
    assert event.reporter_id == 1


@pytest.mark.asyncio
async def test_construct_multiple_fks(db):
    """Event has both tournament (required FK) and reporter (nullable FK)."""
    tournament = Tournament.construct(id=1, name="T")
    reporter = Reporter.construct(id=2, name="R")
    event = Event.construct(name="E", tournament=tournament, reporter=reporter)
    assert event.tournament is tournament
    assert event.tournament_id == 1
    assert event.reporter is reporter
    assert event.reporter_id == 2


@pytest.mark.asyncio
async def test_construct_book_with_author_fk(db):
    """Book has an FK to Author."""
    author = Author.construct(id=1, name="Author")
    book = Book.construct(name="Book", author=author, rating=4.5)
    assert book.author is author
    assert book.author_id == 1
    assert book.rating == 4.5
