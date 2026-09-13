import re
import subprocess  # nosec
import sys

import pytest
import pytest_asyncio

from tests.testmodels import (
    Address,
    Author,
    BookNoConstraint,
    DoubleFK,
    Employee,
    Event,
    Extra,
    M2mWithO2oPk,
    Node,
    O2oPkModelWithM2m,
    Pair,
    Reporter,
    Single,
    Team,
    Tournament,
    UUIDFkRelatedNullModel,
)
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotIn
from tortoise.exceptions import FieldError, NoValuesFetched, OperationalError
from tortoise.functions import Count, Trim

# =============================================================================
# TestRelations - uses db fixture (transaction rollback)
# =============================================================================


@pytest.mark.asyncio
async def test_relations(db):
    tournament = Tournament(name="New Tournament")
    await tournament.save()
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

    with pytest.raises(NoValuesFetched):
        [team.id for team in event.participants]  # pylint: disable=W0104

    teamids = []
    async for team in event.participants:
        teamids.append(team.id)
    assert set(teamids) == {participants[0].id, participants[1].id}
    teamids = [team.id async for team in event.participants]
    assert set(teamids) == {participants[0].id, participants[1].id}

    assert {team.id for team in event.participants} == {participants[0].id, participants[1].id}

    assert event.participants[0].id in {participants[0].id, participants[1].id}

    selected_events = await Event.filter(participants=participants[0].id).prefetch_related(
        "participants", "tournament"
    )
    assert len(selected_events) == 1
    assert selected_events[0].tournament.id == tournament.id
    assert len(selected_events[0].participants) == 2
    await participants[0].fetch_related("events")
    assert participants[0].events[0] == event

    await Team.fetch_for_list(participants, "events")

    await Team.filter(events__tournament__id=tournament.id)

    await Event.filter(tournament=tournament)

    await Tournament.filter(events__name__in=["Test", "Prod"]).distinct()

    result = await Event.filter(pk=event.pk).values(
        "event_id", "name", tournament="tournament__name"
    )
    assert result[0]["tournament"] == tournament.name

    result = await Event.filter(pk=event.pk).values_list("event_id", "participants__name")
    assert len(result) == 2


@pytest.mark.asyncio
async def test_reset_queryset_on_query(db):
    tournament = await Tournament.create(name="New Tournament")
    event = await Event.create(name="Test", tournament_id=tournament.id)
    participants = []
    for i in range(2):
        team = await Team.create(name=f"Team {(i + 1)}")
        participants.append(team)
    await event.participants.add(*participants)
    queryset = Event.all().annotate(count=Count("participants"))
    await queryset.first()
    await queryset.filter(name="Test").first()


@pytest.mark.asyncio
async def test_bool_for_relation_new_object(db):
    tournament = await Tournament.create(name="New Tournament")

    with pytest.raises(NoValuesFetched):
        bool(tournament.events)


@pytest.mark.asyncio
async def test_bool_for_relation_old_object(db):
    await Tournament.create(name="New Tournament")
    tournament = await Tournament.first()

    with pytest.raises(NoValuesFetched):
        bool(tournament.events)


@pytest.mark.asyncio
async def test_bool_for_relation_fetched_false(db):
    tournament = await Tournament.create(name="New Tournament")
    await tournament.fetch_related("events")

    assert not bool(tournament.events)


@pytest.mark.asyncio
async def test_bool_for_relation_fetched_true(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)
    await tournament.fetch_related("events")

    assert bool(tournament.events)


@pytest.mark.asyncio
async def test_m2m_add(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    fetched_event = await Event.first().prefetch_related("participants")
    assert len(fetched_event.participants) == 2


@pytest.mark.asyncio
async def test_m2m_add_already_added(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    await event.participants.add(team, team_second)
    fetched_event = await Event.first().prefetch_related("participants")
    assert len(fetched_event.participants) == 2


@pytest.mark.asyncio
async def test_m2m_clear(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    await event.participants.clear()
    fetched_event = await Event.first().prefetch_related("participants")
    assert len(fetched_event.participants) == 0


@pytest.mark.asyncio
async def test_m2m_remove(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    await event.participants.remove(team)
    fetched_event = await Event.first().prefetch_related("participants")
    assert len(fetched_event.participants) == 1


@pytest.mark.asyncio
async def test_o2o_lazy(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    await Address.create(city="Santa Monica", street="Ocean", event=event)

    fetched_address = await event.address
    assert fetched_address.city == "Santa Monica"


@pytest.mark.asyncio
async def test_m2m_remove_two(db):
    tournament = await Tournament.create(name="tournament")
    event = await Event.create(name="First", tournament=tournament)
    team = await Team.create(name="1")
    team_second = await Team.create(name="2")
    await event.participants.add(team, team_second)
    await event.participants.remove(team, team_second)
    fetched_event = await Event.first().prefetch_related("participants")
    assert len(fetched_event.participants) == 0


@pytest.mark.asyncio
async def test_self_ref(db):
    root = await Employee.create(name="Root")
    loose = await Employee.create(name="Loose")
    _1 = await Employee.create(name="1. First H1", manager=root)
    _2 = await Employee.create(name="2. Second H1", manager=root)
    _1_1 = await Employee.create(name="1.1. First H2", manager=_1)
    _1_1_1 = await Employee.create(name="1.1.1. First H3", manager=_1_1)
    _2_1 = await Employee.create(name="2.1. Second H2", manager=_2)
    _2_2 = await Employee.create(name="2.2. Third H2", manager=_2)

    await _1.talks_to.add(_2, _1_1_1, loose)
    await _2_1.gets_talked_to.add(_2_2, _1_1, loose)

    LOOSE_TEXT = "Loose (to: 2.1. Second H2) (from: 1. First H1)"
    ROOT_TEXT = """Root (to: ) (from: )
  1. First H1 (to: 1.1.1. First H3, 2. Second H1, Loose) (from: )
    1.1. First H2 (to: 2.1. Second H2) (from: )
      1.1.1. First H3 (to: ) (from: 1. First H1)
  2. Second H1 (to: ) (from: 1. First H1)
    2.1. Second H2 (to: ) (from: 1.1. First H2, 2.2. Third H2, Loose)
    2.2. Third H2 (to: 2.1. Second H2) (from: )"""

    # Evaluated off creation objects
    assert await loose.full_hierarchy__async_for() == LOOSE_TEXT
    assert await loose.full_hierarchy__fetch_related() == LOOSE_TEXT
    assert await root.full_hierarchy__async_for() == ROOT_TEXT
    assert await root.full_hierarchy__fetch_related() == ROOT_TEXT

    # Evaluated off new objects -> Result is identical
    root2 = await Employee.get(name="Root")
    loose2 = await Employee.get(name="Loose")
    assert await loose2.full_hierarchy__async_for() == LOOSE_TEXT
    assert await loose2.full_hierarchy__fetch_related() == LOOSE_TEXT
    assert await root2.full_hierarchy__async_for() == ROOT_TEXT
    assert await root2.full_hierarchy__fetch_related() == ROOT_TEXT


@pytest.mark.asyncio
async def test_self_ref_filter_by_child(db):
    root = await Employee.create(name="Root")
    await Employee.create(name="1. First H1", manager=root)
    await Employee.create(name="2. Second H1", manager=root)

    root2 = await Employee.get(team_members__name="1. First H1")
    assert root.id == root2.id


@pytest.mark.asyncio
async def test_self_ref_filter_both(db):
    root = await Employee.create(name="Root")
    await Employee.create(name="1. First H1", manager=root)
    await Employee.create(name="2. Second H1", manager=root)

    root2 = await Employee.get(name="Root", team_members__name="1. First H1")
    assert root.id == root2.id


@pytest.mark.asyncio
async def test_self_ref_annotate(db):
    root = await Employee.create(name="Root")
    await Employee.create(name="Loose")
    await Employee.create(name="1. First H1", manager=root)
    await Employee.create(name="2. Second H1", manager=root)

    root_ann = await Employee.get(name="Root").annotate(num_team_members=Count("team_members"))
    assert root_ann.num_team_members == 2
    root_ann = await Employee.get(name="Loose").annotate(num_team_members=Count("team_members"))
    assert root_ann.num_team_members == 0


@pytest.mark.asyncio
async def test_prefetch_related_fk(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    event2 = await Event.filter(name="Test").prefetch_related("tournament")
    assert event2[0].tournament == tournament


@pytest.mark.asyncio
async def test_prefetch_related_rfk(db):
    tournament = await Tournament.create(name="New Tournament")
    event = await Event.create(name="Test", tournament_id=tournament.id)

    tournament2 = await Tournament.filter(name="New Tournament").prefetch_related("events")
    assert list(tournament2[0].events) == [event]


@pytest.mark.asyncio
async def test_prefetch_related_missing_field(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(FieldError, match="Relation tourn1ment for models.Event not found"):
        await Event.filter(name="Test").prefetch_related("tourn1ment")


@pytest.mark.asyncio
async def test_prefetch_related_nonrel_field(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(FieldError, match="Field modified on models.Event is not a relation"):
        await Event.filter(name="Test").prefetch_related("modified")


@pytest.mark.asyncio
async def test_prefetch_related_id(db):
    tournament = await Tournament.create(name="New Tournament")
    await Event.create(name="Test", tournament_id=tournament.id)

    with pytest.raises(FieldError, match="Field event_id on models.Event is not a relation"):
        await Event.filter(name="Test").prefetch_related("event_id")


@pytest.mark.asyncio
async def test_nullable_fk_raw(db):
    tournament = await Tournament.create(name="New Tournament")
    reporter = await Reporter.create(name="Reporter")
    event1 = await Event.create(name="Without reporter", tournament=tournament)
    event2 = await Event.create(name="With reporter", tournament=tournament, reporter=reporter)

    assert not event1.reporter_id
    assert event2.reporter_id


@pytest.mark.asyncio
async def test_nullable_fk_obj(db):
    tournament = await Tournament.create(name="New Tournament")
    reporter = await Reporter.create(name="Reporter")
    event1 = await Event.create(name="Without reporter", tournament=tournament)
    event2 = await Event.create(name="With reporter", tournament=tournament, reporter=reporter)

    assert not event1.reporter
    assert event2.reporter


@pytest.mark.asyncio
async def test_db_constraint(db):
    author = await Author.create(name="Some One")
    book = await BookNoConstraint.create(name="First!", author=author, rating=4)
    book = await BookNoConstraint.all().select_related("author").get(pk=book.pk)
    assert author.pk == book.author.pk


@pytest.mark.asyncio
async def test_select_related_with_annotation(db):
    tournament = await Tournament.create(name="New Tournament")
    reporter = await Reporter.create(name="Reporter")
    event = await Event.create(name="With reporter", tournament=tournament, reporter=reporter)
    event = (
        await Event.filter(pk=event.pk)
        .select_related("reporter")
        .annotate(tournament_name=Trim("tournament__name"))
        .first()
    )
    assert event.reporter == reporter
    assert hasattr(event, "tournament_name")
    assert event.tournament_name == tournament.name


@pytest.mark.asyncio
async def test_select_related_sets_null_for_null_fk(db):
    """Test that select related yields null for fields with nulled fk cols."""
    related_dude = await UUIDFkRelatedNullModel.create(name="Some model")
    await related_dude.fetch_related("parent")  # that is strange :)
    related_dude_fresh = (
        await UUIDFkRelatedNullModel.all().select_related("parent").get(id=related_dude.id)
    )
    assert related_dude_fresh.parent is None
    assert related_dude_fresh.parent == related_dude.parent


@pytest.mark.asyncio
async def test_select_related_sets_valid_nulls(db) -> None:
    """When we select related objects, the data we get from db should be set to corresponding attribute."""
    left_2nd_lvl = await DoubleFK.create(name="second leaf")
    left_1st_lvl = await DoubleFK.create(name="1st", left=left_2nd_lvl)
    root = await DoubleFK.create(name="root", left=left_1st_lvl)

    retrieved_root = (
        await DoubleFK.all().select_related("left__left__left", "right").get(id=root.pk)
    )
    assert retrieved_root.right is None
    assert retrieved_root.left is not None
    assert retrieved_root.left == left_1st_lvl
    assert retrieved_root.left.left == left_2nd_lvl


@pytest.mark.asyncio
async def test_no_ambiguous_fk_relations_set(db):
    """Basic select_related test cases provided by @https://github.com/Terrance.

    The idea was that on the moment of writing this feature, there were no way to correctly set attributes for
    select_related fields attributes.
    src: https://github.com/tortoise/tortoise-orm/pull/826#issuecomment-883341557
    """

    extra = await Extra.create()
    single = await Single.create(extra=extra)
    await Pair.create(right=single)
    pair = (
        await Pair.filter(id=1).select_related("left", "left__extra", "right", "right__extra").get()
    )
    assert pair.left is None
    assert pair.right.extra == extra
    single = await Single.create()
    await Pair.create(right=single)
    pair = (
        await Pair.filter(id=2).select_related("left", "left__extra", "right", "right__extra").get()
    )
    assert pair.right.extra is None  # should be None


@requireCapability(dialect=NotIn("mssql", "mysql"))
@pytest.mark.asyncio
async def test_0_value_fk(db):
    """ForegnKeyField should exits even if the the source_field looks like false, but not None
    src: https://github.com/tortoise/tortoise-orm/issues/1274
    """
    extra = await Extra.create(id=0)
    single = await Single.create(extra=extra)

    single_reload = await Single.get(id=single.id)
    assert (await single_reload.extra).id == 0

    tournament_0 = await Tournament.create(name="tournament zero", id=0)
    await Event.create(name="event-zero", tournament=tournament_0)

    e = await Event.get(name="event-zero")
    id_before_fetch = e.tournament_id
    await e.fetch_related("tournament")
    id_after_fetch = e.tournament_id
    assert id_before_fetch == id_after_fetch

    event_0 = await Event.get(name="event-zero").prefetch_related("tournament")
    assert event_0.tournament == tournament_0


# =============================================================================
# TestDoubleFK - uses db fixture with setup data
# =============================================================================


# Regex patterns for SQL query validation
_select_match = r'SELECT [`"]doublefk[`"].[`"]name[`"] [`"]name[`"]'
_select1_match = r'[`"]doublefk__left[`"].[`"]name[`"] [`"]left__name[`"]'
_select2_match = r'[`"]doublefk__right[`"].[`"]name[`"] [`"]right__name[`"]'
_join1_match = (
    r'LEFT OUTER JOIN [`"]doublefk[`"] [`"]doublefk__left[`"] ON '
    r'[`"]doublefk__left[`"].[`"]id[`"]=[`"]doublefk[`"].[`"]left_id[`"]'
)
_join2_match = (
    r'LEFT OUTER JOIN [`"]doublefk[`"] [`"]doublefk__right[`"] ON '
    r'[`"]doublefk__right[`"].[`"]id[`"]=[`"]doublefk[`"].[`"]right_id[`"]'
)


@pytest_asyncio.fixture
async def doublefk_data(db):
    """Build DoubleFK test data."""
    one = await DoubleFK.create(name="one")
    two = await DoubleFK.create(name="two")
    middle = await DoubleFK.create(name="middle", left=one, right=two)
    return middle


@pytest.mark.asyncio
async def test_doublefk_filter(db, doublefk_data):
    middle = doublefk_data
    qset = DoubleFK.filter(left__name="one")
    result = await qset
    query = qset.query.get_sql()

    assert re.search(_join1_match, query)
    assert result == [middle]


@pytest.mark.asyncio
async def test_doublefk_filter_values(db, doublefk_data):
    qset = DoubleFK.filter(left__name="one").values("name")
    result = await qset
    query = qset.query.get_sql()

    assert re.search(_select_match, query)
    assert re.search(_join1_match, query)
    assert result == [{"name": "middle"}]


@pytest.mark.asyncio
async def test_doublefk_filter_values_rel(db, doublefk_data):
    qset = DoubleFK.filter(left__name="one").values("name", "left__name")
    result = await qset
    query = qset.query.get_sql()

    assert re.search(_select_match, query)
    assert re.search(_select1_match, query)
    assert re.search(_join1_match, query)
    assert result == [{"name": "middle", "left__name": "one"}]


@pytest.mark.asyncio
async def test_doublefk_filter_both(db, doublefk_data):
    middle = doublefk_data
    qset = DoubleFK.filter(left__name="one", right__name="two")
    result = await qset
    query = qset.query.get_sql()

    assert re.search(_join1_match, query)
    assert re.search(_join2_match, query)
    assert result == [middle]


@pytest.mark.asyncio
async def test_doublefk_filter_both_values(db, doublefk_data):
    qset = DoubleFK.filter(left__name="one", right__name="two").values("name")
    result = await qset
    query = qset.query.get_sql()

    assert re.search(_select_match, query)
    assert re.search(_join1_match, query)
    assert re.search(_join2_match, query)
    assert result == [{"name": "middle"}]


@pytest.mark.asyncio
async def test_doublefk_filter_both_values_rel(db, doublefk_data):
    qset = DoubleFK.filter(left__name="one", right__name="two").values(
        "name", "left__name", "right__name"
    )
    result = await qset
    query = qset.query.get_sql()

    assert re.search(_select_match, query)
    assert re.search(_select1_match, query)
    assert re.search(_select2_match, query)
    assert re.search(_join1_match, query)
    assert re.search(_join2_match, query)
    assert result == [{"name": "middle", "left__name": "one", "right__name": "two"}]


@pytest.mark.asyncio
async def test_many2many_field_with_o2o_fk(db):
    tournament = await Tournament.create(name="t")
    event = await Event.create(name="e", tournament=tournament)
    address = await Address.create(city="c", street="s", event=event)
    obj = await M2mWithO2oPk.create(name="m")
    assert await obj.address.all() == []
    await obj.address.add(address)
    assert await obj.address.all() == [address]


@pytest.mark.asyncio
async def test_o2o_fk_model_with_m2m_field(db):
    author = await Author.create(name="a")
    obj = await O2oPkModelWithM2m.create(author=author)
    node = await Node.create(name="n")
    assert await obj.nodes.all() == []
    await obj.nodes.add(node)
    assert await obj.nodes.all() == [node]


@pytest.mark.asyncio
async def test_reverse_relation_create_fk(db):
    tournament = await Tournament.create(name="Test Tournament")
    assert await tournament.events.all() == []

    event = await tournament.events.create(name="Test Event")

    await tournament.fetch_related("events")

    assert len(tournament.events) == 1
    assert event.name == "Test Event"
    assert event.tournament_id == tournament.id
    assert tournament.events[0].event_id == event.event_id


@pytest.mark.asyncio
async def test_reverse_relation_create_fk_errors_for_unsaved_instance(db):
    tournament = Tournament(name="Unsaved Tournament")

    # Should raise OperationalError since tournament isn't saved
    with pytest.raises(OperationalError) as cm:
        await tournament.events.create(name="Test Event")

    assert "hasn't been instanced" in str(cm.value)


@requireCapability(dialect="sqlite")
@pytest.mark.asyncio
async def test_recursive(db) -> None:
    file = "examples/relations_recursive.py"
    r = subprocess.run([sys.executable, file], capture_output=True, text=True)  # nosec
    assert r.returncode == 0, f"Script failed (rc={r.returncode}): {r.stderr}"
    output = r.stdout
    s = "2.1. Second H2 (to: ) (from: 2.2. Third H2, Loose, 1.1. First H2)"
    assert s in output
