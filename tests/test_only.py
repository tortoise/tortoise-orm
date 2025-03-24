from tests.testmodels import DoubleFK, Event, SourceFields, StraightFields, Tournament
from tortoise.contrib import test
from tortoise.exceptions import IncompleteInstanceError


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
