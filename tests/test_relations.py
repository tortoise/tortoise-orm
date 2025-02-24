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
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotIn
from tortoise.exceptions import FieldError, NoValuesFetched
from tortoise.functions import Count, Trim


class TestRelations(test.TestCase):
    async def test_relations(self):
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

        with self.assertRaises(NoValuesFetched):
            [team.id for team in event.participants]  # pylint: disable=W0104

        teamids = []
        async for team in event.participants:
            teamids.append(team.id)
        self.assertEqual(set(teamids), {participants[0].id, participants[1].id})
        teamids = [team.id async for team in event.participants]
        self.assertEqual(set(teamids), {participants[0].id, participants[1].id})

        self.assertEqual(
            {team.id for team in event.participants}, {participants[0].id, participants[1].id}
        )

        self.assertIn(event.participants[0].id, {participants[0].id, participants[1].id})

        selected_events = await Event.filter(participants=participants[0].id).prefetch_related(
            "participants", "tournament"
        )
        self.assertEqual(len(selected_events), 1)
        self.assertEqual(selected_events[0].tournament.id, tournament.id)
        self.assertEqual(len(selected_events[0].participants), 2)
        await participants[0].fetch_related("events")
        self.assertEqual(participants[0].events[0], event)

        await Team.fetch_for_list(participants, "events")

        await Team.filter(events__tournament__id=tournament.id)

        await Event.filter(tournament=tournament)

        await Tournament.filter(events__name__in=["Test", "Prod"]).distinct()

        result = await Event.filter(pk=event.pk).values(
            "event_id", "name", tournament="tournament__name"
        )
        self.assertEqual(result[0]["tournament"], tournament.name)

        result = await Event.filter(pk=event.pk).values_list("event_id", "participants__name")
        self.assertEqual(len(result), 2)

    async def test_reset_queryset_on_query(self):
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

    async def test_bool_for_relation_new_object(self):
        tournament = await Tournament.create(name="New Tournament")

        with self.assertRaises(NoValuesFetched):
            bool(tournament.events)

    async def test_bool_for_relation_old_object(self):
        await Tournament.create(name="New Tournament")
        tournament = await Tournament.first()

        with self.assertRaises(NoValuesFetched):
            bool(tournament.events)

    async def test_bool_for_relation_fetched_false(self):
        tournament = await Tournament.create(name="New Tournament")
        await tournament.fetch_related("events")

        self.assertFalse(bool(tournament.events))

    async def test_bool_for_relation_fetched_true(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)
        await tournament.fetch_related("events")

        self.assertTrue(bool(tournament.events))

    async def test_m2m_add(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 2)

    async def test_m2m_add_already_added(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        await event.participants.add(team, team_second)
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 2)

    async def test_m2m_clear(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        await event.participants.clear()
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 0)

    async def test_m2m_remove(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        await event.participants.remove(team)
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 1)

    async def test_o2o_lazy(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        await Address.create(city="Santa Monica", street="Ocean", event=event)

        fetched_address = await event.address
        self.assertEqual(fetched_address.city, "Santa Monica")

    async def test_m2m_remove_two(self):
        tournament = await Tournament.create(name="tournament")
        event = await Event.create(name="First", tournament=tournament)
        team = await Team.create(name="1")
        team_second = await Team.create(name="2")
        await event.participants.add(team, team_second)
        await event.participants.remove(team, team_second)
        fetched_event = await Event.first().prefetch_related("participants")
        self.assertEqual(len(fetched_event.participants), 0)

    async def test_self_ref(self):
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
        self.assertEqual(await loose.full_hierarchy__async_for(), LOOSE_TEXT)
        self.assertEqual(await loose.full_hierarchy__fetch_related(), LOOSE_TEXT)
        self.assertEqual(await root.full_hierarchy__async_for(), ROOT_TEXT)
        self.assertEqual(await root.full_hierarchy__fetch_related(), ROOT_TEXT)

        # Evaluated off new objects → Result is identical
        root2 = await Employee.get(name="Root")
        loose2 = await Employee.get(name="Loose")
        self.assertEqual(await loose2.full_hierarchy__async_for(), LOOSE_TEXT)
        self.assertEqual(await loose2.full_hierarchy__fetch_related(), LOOSE_TEXT)
        self.assertEqual(await root2.full_hierarchy__async_for(), ROOT_TEXT)
        self.assertEqual(await root2.full_hierarchy__fetch_related(), ROOT_TEXT)

    async def test_self_ref_filter_by_child(self):
        root = await Employee.create(name="Root")
        await Employee.create(name="1. First H1", manager=root)
        await Employee.create(name="2. Second H1", manager=root)

        root2 = await Employee.get(team_members__name="1. First H1")
        self.assertEqual(root.id, root2.id)

    async def test_self_ref_filter_both(self):
        root = await Employee.create(name="Root")
        await Employee.create(name="1. First H1", manager=root)
        await Employee.create(name="2. Second H1", manager=root)

        root2 = await Employee.get(name="Root", team_members__name="1. First H1")
        self.assertEqual(root.id, root2.id)

    async def test_self_ref_annotate(self):
        root = await Employee.create(name="Root")
        await Employee.create(name="Loose")
        await Employee.create(name="1. First H1", manager=root)
        await Employee.create(name="2. Second H1", manager=root)

        root_ann = await Employee.get(name="Root").annotate(num_team_members=Count("team_members"))
        self.assertEqual(root_ann.num_team_members, 2)
        root_ann = await Employee.get(name="Loose").annotate(num_team_members=Count("team_members"))
        self.assertEqual(root_ann.num_team_members, 0)

    async def test_prefetch_related_fk(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        event2 = await Event.filter(name="Test").prefetch_related("tournament")
        self.assertEqual(event2[0].tournament, tournament)

    async def test_prefetch_related_rfk(self):
        tournament = await Tournament.create(name="New Tournament")
        event = await Event.create(name="Test", tournament_id=tournament.id)

        tournament2 = await Tournament.filter(name="New Tournament").prefetch_related("events")
        self.assertEqual(list(tournament2[0].events), [event])

    async def test_prefetch_related_missing_field(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, "Relation tourn1ment for models.Event not found"):
            await Event.filter(name="Test").prefetch_related("tourn1ment")

    async def test_prefetch_related_nonrel_field(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, "Field modified on models.Event is not a relation"):
            await Event.filter(name="Test").prefetch_related("modified")

    async def test_prefetch_related_id(self):
        tournament = await Tournament.create(name="New Tournament")
        await Event.create(name="Test", tournament_id=tournament.id)

        with self.assertRaisesRegex(FieldError, "Field event_id on models.Event is not a relation"):
            await Event.filter(name="Test").prefetch_related("event_id")

    async def test_nullable_fk_raw(self):
        tournament = await Tournament.create(name="New Tournament")
        reporter = await Reporter.create(name="Reporter")
        event1 = await Event.create(name="Without reporter", tournament=tournament)
        event2 = await Event.create(name="With reporter", tournament=tournament, reporter=reporter)

        self.assertFalse(event1.reporter_id)
        self.assertTrue(event2.reporter_id)

    async def test_nullable_fk_obj(self):
        tournament = await Tournament.create(name="New Tournament")
        reporter = await Reporter.create(name="Reporter")
        event1 = await Event.create(name="Without reporter", tournament=tournament)
        event2 = await Event.create(name="With reporter", tournament=tournament, reporter=reporter)

        self.assertFalse(event1.reporter)
        self.assertTrue(event2.reporter)

    async def test_db_constraint(self):
        author = await Author.create(name="Some One")
        book = await BookNoConstraint.create(name="First!", author=author, rating=4)
        book = await BookNoConstraint.all().select_related("author").get(pk=book.pk)
        self.assertEqual(author.pk, book.author.pk)

    async def test_select_related_with_annotation(self):
        tournament = await Tournament.create(name="New Tournament")
        reporter = await Reporter.create(name="Reporter")
        event = await Event.create(name="With reporter", tournament=tournament, reporter=reporter)
        event = (
            await Event.filter(pk=event.pk)
            .select_related("reporter")
            .annotate(tournament_name=Trim("tournament__name"))
            .first()
        )
        self.assertEqual(event.reporter, reporter)
        self.assertTrue(hasattr(event, "tournament_name"))
        self.assertEqual(event.tournament_name, tournament.name)

    async def test_select_related_sets_null_for_null_fk(self):
        """Test that select related yields null for fields with nulled fk cols."""
        related_dude = await UUIDFkRelatedNullModel.create(name="Some model")
        await related_dude.fetch_related("parent")  # that is strange :)
        related_dude_fresh = (
            await UUIDFkRelatedNullModel.all().select_related("parent").get(id=related_dude.id)
        )
        self.assertIsNone(related_dude_fresh.parent)
        self.assertEqual(related_dude_fresh.parent, related_dude.parent)

    async def test_select_related_sets_valid_nulls(self) -> None:
        """When we select related objects, the data we get from db should be set to corresponding attribute."""
        left_2nd_lvl = await DoubleFK.create(name="second leaf")
        left_1st_lvl = await DoubleFK.create(name="1st", left=left_2nd_lvl)
        root = await DoubleFK.create(name="root", left=left_1st_lvl)

        retrieved_root = (
            await DoubleFK.all().select_related("left__left__left", "right").get(id=root.pk)
        )
        self.assertIsNone(retrieved_root.right)
        assert retrieved_root.left is not None
        self.assertEqual(retrieved_root.left, left_1st_lvl)
        self.assertEqual(retrieved_root.left.left, left_2nd_lvl)

    async def test_no_ambiguous_fk_relations_set(self):
        """Basic select_related test cases provided by @https://github.com/Terrance.

        The idea was that on the moment of writing this feature, there were no way to correctly set attributes for
        select_related fields attributes.
        src: https://github.com/tortoise/tortoise-orm/pull/826#issuecomment-883341557
        """

        extra = await Extra.create()
        single = await Single.create(extra=extra)
        await Pair.create(right=single)
        pair = (
            await Pair.filter(id=1)
            .select_related("left", "left__extra", "right", "right__extra")
            .get()
        )
        self.assertIsNone(pair.left)
        self.assertEqual(pair.right.extra, extra)
        single = await Single.create()
        await Pair.create(right=single)
        pair = (
            await Pair.filter(id=2)
            .select_related("left", "left__extra", "right", "right__extra")
            .get()
        )
        self.assertIsNone(pair.right.extra)  # should be None

    @test.requireCapability(dialect=NotIn("mssql", "mysql"))
    async def test_0_value_fk(self):
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
        self.assertEqual(id_before_fetch, id_after_fetch)

        event_0 = await Event.get(name="event-zero").prefetch_related("tournament")
        self.assertEqual(event_0.tournament, tournament_0)


class TestDoubleFK(test.TestCase):
    select_match = r'SELECT [`"]doublefk[`"].[`"]name[`"] [`"]name[`"]'
    select1_match = r'[`"]doublefk__left[`"].[`"]name[`"] [`"]left__name[`"]'
    select2_match = r'[`"]doublefk__right[`"].[`"]name[`"] [`"]right__name[`"]'
    join1_match = (
        r'LEFT OUTER JOIN [`"]doublefk[`"] [`"]doublefk__left[`"] ON '
        r'[`"]doublefk__left[`"].[`"]id[`"]=[`"]doublefk[`"].[`"]left_id[`"]'
    )
    join2_match = (
        r'LEFT OUTER JOIN [`"]doublefk[`"] [`"]doublefk__right[`"] ON '
        r'[`"]doublefk__right[`"].[`"]id[`"]=[`"]doublefk[`"].[`"]right_id[`"]'
    )

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        one = await DoubleFK.create(name="one")
        two = await DoubleFK.create(name="two")
        self.middle = await DoubleFK.create(name="middle", left=one, right=two)

    async def test_doublefk_filter(self):
        qset = DoubleFK.filter(left__name="one")
        result = await qset
        query = qset.query.get_sql()

        self.assertRegex(query, self.join1_match)
        self.assertEqual(result, [self.middle])

    async def test_doublefk_filter_values(self):
        qset = DoubleFK.filter(left__name="one").values("name")
        result = await qset
        query = qset.query.get_sql()

        self.assertRegex(query, self.select_match)
        self.assertRegex(query, self.join1_match)
        self.assertEqual(result, [{"name": "middle"}])

    async def test_doublefk_filter_values_rel(self):
        qset = DoubleFK.filter(left__name="one").values("name", "left__name")
        result = await qset
        query = qset.query.get_sql()

        self.assertRegex(query, self.select_match)
        self.assertRegex(query, self.select1_match)
        self.assertRegex(query, self.join1_match)
        self.assertEqual(result, [{"name": "middle", "left__name": "one"}])

    async def test_doublefk_filter_both(self):
        qset = DoubleFK.filter(left__name="one", right__name="two")
        result = await qset
        query = qset.query.get_sql()

        self.assertRegex(query, self.join1_match)
        self.assertRegex(query, self.join2_match)
        self.assertEqual(result, [self.middle])

    async def test_doublefk_filter_both_values(self):
        qset = DoubleFK.filter(left__name="one", right__name="two").values("name")
        result = await qset
        query = qset.query.get_sql()

        self.assertRegex(query, self.select_match)
        self.assertRegex(query, self.join1_match)
        self.assertRegex(query, self.join2_match)
        self.assertEqual(result, [{"name": "middle"}])

    async def test_doublefk_filter_both_values_rel(self):
        qset = DoubleFK.filter(left__name="one", right__name="two").values(
            "name", "left__name", "right__name"
        )
        result = await qset
        query = qset.query.get_sql()

        self.assertRegex(query, self.select_match)
        self.assertRegex(query, self.select1_match)
        self.assertRegex(query, self.select2_match)
        self.assertRegex(query, self.join1_match)
        self.assertRegex(query, self.join2_match)
        self.assertEqual(result, [{"name": "middle", "left__name": "one", "right__name": "two"}])

    async def test_many2many_field_with_o2o_fk(self):
        tournament = await Tournament.create(name="t")
        event = await Event.create(name="e", tournament=tournament)
        address = await Address.create(city="c", street="s", event=event)
        obj = await M2mWithO2oPk.create(name="m")
        self.assertEqual(await obj.address.all(), [])
        await obj.address.add(address)
        self.assertEqual(await obj.address.all(), [address])

    async def test_o2o_fk_model_with_m2m_field(self):
        author = await Author.create(name="a")
        obj = await O2oPkModelWithM2m.create(author=author)
        node = await Node.create(name="n")
        self.assertEqual(await obj.nodes.all(), [])
        await obj.nodes.add(node)
        self.assertEqual(await obj.nodes.all(), [node])
