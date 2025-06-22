from tests.testmodels import DoubleFK, Event, SourceFields, StraightFields, Tournament
from tortoise.contrib import test
from tortoise.exceptions import FieldError, IncompleteInstanceError
from tortoise.functions import Count


class TestOnlyStraight(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.model = StraightFields
        self.instance = await self.model.create(chars="Test")

    async def test_get(self):
        instance_part = await self.model.get(chars="Test").only("chars", "blip")

        self.assertEqual(instance_part.chars, "Test")
        with self.assertRaises(AttributeError):
            _ = instance_part.nullable

    async def test_filter(self):
        instances = await self.model.filter(chars="Test").only("chars", "blip")

        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].chars, "Test")
        with self.assertRaises(AttributeError):
            _ = instances[0].nullable

    async def test_first(self):
        instance_part = await self.model.filter(chars="Test").only("chars", "blip").first()

        self.assertEqual(instance_part.chars, "Test")
        with self.assertRaises(AttributeError):
            _ = instance_part.nullable

    async def test_save(self):
        instance_part = await self.model.get(chars="Test").only("chars", "blip")

        with self.assertRaisesRegex(IncompleteInstanceError, " is a partial model"):
            await instance_part.save()

    async def test_partial_save(self):
        instance_part = await self.model.get(chars="Test").only("chars", "blip")

        with self.assertRaisesRegex(IncompleteInstanceError, "Partial update not available"):
            await instance_part.save(update_fields=["chars"])

    async def test_partial_save_with_pk_wrong_field(self):
        instance_part = await self.model.get(chars="Test").only("chars", "eyedee")

        with self.assertRaisesRegex(IncompleteInstanceError, "field 'nullable' is not available"):
            await instance_part.save(update_fields=["nullable"])

    async def test_partial_save_with_pk(self):
        instance_part = await self.model.get(chars="Test").only("chars", "eyedee")

        instance_part.chars = "Test1"
        await instance_part.save(update_fields=["chars"])

        instance2 = await self.model.get(pk=self.instance.pk)
        self.assertEqual(instance2.chars, "Test1")


class TestOnlySource(TestOnlyStraight):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.model = SourceFields  # type: ignore
        self.instance = await self.model.create(chars="Test")


class TestOnlyRecursive(test.TestCase):
    async def test_one_level(self):
        left_1st_lvl = await DoubleFK.create(name="1st")
        root = await DoubleFK.create(name="root", left=left_1st_lvl)

        ret = (
            await DoubleFK.filter(pk=root.pk).only("name", "left__name", "left__left__name").first()
        )
        self.assertIsNotNone(ret)
        with self.assertRaises(AttributeError):
            _ = ret.id
        self.assertEqual(ret.name, "root")
        self.assertEqual(ret.left.name, "1st")
        with self.assertRaises(AttributeError):
            _ = ret.left.id
        with self.assertRaises(AttributeError):
            _ = ret.right

    async def test_two_levels(self):
        left_2nd_lvl = await DoubleFK.create(name="second leaf")
        left_1st_lvl = await DoubleFK.create(name="1st", left=left_2nd_lvl)
        root = await DoubleFK.create(name="root", left=left_1st_lvl)

        ret = (
            await DoubleFK.filter(pk=root.pk).only("name", "left__name", "left__left__name").first()
        )
        self.assertIsNotNone(ret)
        with self.assertRaises(AttributeError):
            _ = ret.id
        self.assertEqual(ret.name, "root")
        self.assertEqual(ret.left.name, "1st")
        with self.assertRaises(AttributeError):
            _ = ret.left.id
        self.assertEqual(ret.left.left.name, "second leaf")

    async def test_two_levels_reverse_argument_order(self):
        left_2nd_lvl = await DoubleFK.create(name="second leaf")
        left_1st_lvl = await DoubleFK.create(name="1st", left=left_2nd_lvl)
        root = await DoubleFK.create(name="root", left=left_1st_lvl)

        ret = (
            await DoubleFK.filter(pk=root.pk).only("left__left__name", "left__name", "name").first()
        )
        self.assertIsNotNone(ret)
        with self.assertRaises(AttributeError):
            _ = ret.id
        self.assertEqual(ret.name, "root")
        self.assertEqual(ret.left.name, "1st")
        with self.assertRaises(AttributeError):
            _ = ret.left.id
        self.assertEqual(ret.left.left.name, "second leaf")


class TestOnlyRelated(test.TestCase):
    async def test_related_one_level(self):
        tournament = await Tournament.create(name="New Tournament", desc="New Description")
        await Event.create(name="Event 1", tournament=tournament)
        await Event.create(name="Event 2", tournament=tournament)

        ret = (
            await Event.filter(tournament=tournament)
            .only("name", "tournament__name")
            .order_by("name")
        )
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[0].name, "Event 1")
        with self.assertRaises(AttributeError):
            _ = ret[0].alias
        self.assertEqual(ret[1].name, "Event 2")
        with self.assertRaises(AttributeError):
            _ = ret[1].alias
        self.assertEqual(ret[0].tournament.name, "New Tournament")
        with self.assertRaises(AttributeError):
            _ = ret[0].tournament.id
        with self.assertRaises(AttributeError):
            _ = ret[0].tournament.desc

    async def test_related_one_level_reversed_argument_order(self):
        tournament = await Tournament.create(name="New Tournament", desc="New Description")
        await Event.create(name="Event 1", tournament=tournament)
        await Event.create(name="Event 2", tournament=tournament)

        ret = (
            await Event.filter(tournament=tournament)
            .only("tournament__name", "name")
            .order_by("name")
        )
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[0].name, "Event 1")
        self.assertEqual(ret[0].tournament.name, "New Tournament")

    async def test_just_related(self):
        tournament = await Tournament.create(name="New Tournament", desc="New Description")
        await Event.create(name="Event 1", tournament=tournament)
        await Event.create(name="Event 2", tournament=tournament)

        ret = (
            await Event.filter(tournament=tournament)
            .only("tournament__name")
            .order_by("name")
            .all()
        )
        self.assertEqual(len(ret), 2)
        self.assertEqual(ret[0].tournament.name, "New Tournament")
        self.assertEqual(ret[1].tournament.name, "New Tournament")


class TestOnlyAdvanced(test.TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.tournament = await Tournament.create(name="Tournament A", desc="Description A")
        self.event1 = await Event.create(name="Event 1", tournament=self.tournament)
        self.event2 = await Event.create(name="Event 2", tournament=self.tournament)

    async def test_exclude(self):
        """Test .only() combined with .exclude()"""
        events = await Event.filter(tournament=self.tournament).exclude(name="Event 2").only("name")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Event 1")
        with self.assertRaises(AttributeError):
            _ = events[0].modified

    async def test_limit(self):
        """Test .only() combined with .limit()"""
        events = await Event.all().only("name").limit(1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Event 1")  # Assumes ordering by PK
        with self.assertRaises(AttributeError):
            _ = events[0].modified

    async def test_distinct(self):
        """Test .only() combined with .distinct()"""
        # Create duplicate event names
        await Event.create(name="Event 1", tournament=self.tournament)

        events = await Event.all().only("name").distinct()
        # Should only have 2 distinct event names
        self.assertEqual(len(events), 2)
        event_names = {e.name for e in events}
        self.assertEqual(event_names, {"Event 1", "Event 2"})

    async def test_values(self):
        """Test .only() combined with .values()"""
        with self.assertRaises(ValueError, msg="values() cannot be used with .only()"):
            await Event.all().only("name").values("name")

    async def test_pk_field(self):
        """Test .only() with just the primary key field"""
        tournament = await Tournament.first().only("id")
        self.assertIsNotNone(tournament.id)
        with self.assertRaises(AttributeError):
            _ = tournament.name

    async def test_empty(self):
        """Test .only() with no fields (should raise an error)"""
        with self.assertRaises(ValueError):
            await Event.all().only()

    async def test_annotate(self):
        tournaments = await Tournament.annotate(event_count=Count("events")).only(
            "name", "event_count"
        )

        self.assertEqual(tournaments[0].name, "Tournament A")
        self.assertEqual(tournaments[0].event_count, 2)
        with self.assertRaises(AttributeError):
            _ = tournaments[0].desc

    async def test_nonexistent_field(self):
        """Test .only() with a field that doesn't exist"""
        with self.assertRaises(FieldError):
            await Event.all().only("nonexistent_field").all()

    async def test_join_in_filter(self):
        event = await Event.filter(name="Event 1").only("name").first()
        self.assertEqual(event.name, "Event 1")
        with self.assertRaises(AttributeError):
            _ = event.tournament

        event = await Event.filter(tournament__name="Tournament A").only("name").first()
        self.assertEqual(event.name, "Event 1")
        with self.assertRaises(AttributeError):
            _ = event.tournament

        event = (
            await Event.filter(tournament__name="Tournament A")
            .only("name", "tournament__name")
            .first()
        )
        self.assertEqual(event.name, "Event 1")
        self.assertEqual(event.tournament.name, "Tournament A")

    async def test_join_in_order_by(self):
        events = await Event.all().order_by("name").only("name")
        self.assertEqual(events[0].name, "Event 1")
        with self.assertRaises(AttributeError):
            _ = events[0].tournament

        events = await Event.all().order_by("tournament__name", "name").only("name")
        self.assertEqual(events[0].name, "Event 1")
        with self.assertRaises(AttributeError):
            _ = events[0].tournament

        events = (
            await Event.all().order_by("tournament__name", "name").only("name", "tournament__name")
        )
        self.assertEqual(events[0].name, "Event 1")
        self.assertEqual(events[0].tournament.name, "Tournament A")

    async def test_select_related(self):
        """Test .only() with .select_related() for basic functionality"""
        event = (
            await Event.filter(name="Event 1")
            .select_related("tournament")
            .only("name", "tournament__name")
            .first()
        )

        self.assertEqual(event.name, "Event 1")
        self.assertEqual(event.tournament.name, "Tournament A")

        with self.assertRaises(AttributeError):
            _ = event.id
        with self.assertRaises(AttributeError):
            _ = event.tournament.id
