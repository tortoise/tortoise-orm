from tortoise.contrib import test
from tortoise.exceptions import IntegrityError, NoValuesFetched, OperationalError
from tortoise.tests import testmodels


class TestForeignKeyUUIDField(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.UUIDFkRelatedModel.create()

    async def test_create_by_id(self):
        tour = await testmodels.UUIDPkModel.create()
        rel = await testmodels.UUIDFkRelatedModel.create(model_id=tour.id)
        self.assertEqual(rel.model_id, tour.id)
        self.assertEqual((await tour.children.all())[0], rel)

    async def test_create_by_name(self):
        tour = await testmodels.UUIDPkModel.create()
        rel = await testmodels.UUIDFkRelatedModel.create(model=tour)
        await rel.fetch_related("model")
        self.assertEqual(rel.model, tour)
        self.assertEqual((await tour.children.all())[0], rel)

    @test.skip("Not yet implemented")
    async def test_by_name__unfetched(self):
        tour = await testmodels.UUIDPkModel.create()
        rel = await testmodels.UUIDFkRelatedModel.create(model=tour)
        with self.assertRaisesRegex(NoValuesFetched, "moo"):
            rel.model  # pylint: disable=W0104

    @test.skip("Not yet implemented")
    async def test_by_name__awaited(self):
        tour = await testmodels.UUIDPkModel.create()
        rel = await testmodels.UUIDFkRelatedModel.create(model=tour)
        self.assertEqual(await rel.model, tour)
        self.assertEqual((await tour.children.all())[0], rel)

    async def test_update_by_name(self):
        tour = await testmodels.UUIDPkModel.create()
        tour2 = await testmodels.UUIDPkModel.create()
        rel0 = await testmodels.UUIDFkRelatedModel.create(model=tour)

        await testmodels.UUIDFkRelatedModel.filter(id=rel0.id).update(model=tour2)
        rel = await testmodels.UUIDFkRelatedModel.get(id=rel0.id)

        await rel.fetch_related("model")
        self.assertEqual(rel.model, tour2)
        self.assertEqual(await tour.children.all(), [])
        self.assertEqual((await tour2.children.all())[0], rel)

    async def test_update_by_id(self):
        tour = await testmodels.UUIDPkModel.create()
        tour2 = await testmodels.UUIDPkModel.create()
        rel0 = await testmodels.UUIDFkRelatedModel.create(model_id=tour.id)

        await testmodels.UUIDFkRelatedModel.filter(id=rel0.id).update(model_id=tour2.id)
        rel = await testmodels.UUIDFkRelatedModel.get(id=rel0.id)

        self.assertEqual(rel.model_id, tour2.id)
        self.assertEqual(await tour.children.all(), [])
        self.assertEqual((await tour2.children.all())[0], rel)

    async def test_uninstantiated_create(self):
        tour = testmodels.UUIDPkModel()
        with self.assertRaisesRegex(OperationalError, "You should first call .save()"):
            await testmodels.UUIDFkRelatedModel.create(model=tour)

    async def test_uninstantiated_iterate(self):
        tour = testmodels.UUIDPkModel()
        with self.assertRaisesRegex(
            OperationalError, "This objects hasn't been instanced, call .save()"
        ):
            async for _ in tour.children:
                pass

    async def test_uninstantiated_await(self):
        tour = testmodels.UUIDPkModel()
        with self.assertRaisesRegex(
            OperationalError, "This objects hasn't been instanced, call .save()"
        ):
            await tour.children

    async def test_unfetched_contains(self):
        tour = await testmodels.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            "a" in tour.children  # pylint: disable=W0104

    async def test_unfetched_iter(self):
        tour = await testmodels.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            for _ in tour.children:
                pass

    async def test_unfetched_len(self):
        tour = await testmodels.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            len(tour.children)

    async def test_unfetched_bool(self):
        tour = await testmodels.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            bool(tour.children)

    async def test_unfetched_getitem(self):
        tour = await testmodels.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            tour.children[0]  # pylint: disable=W0104

    async def test_instantiated_create(self):
        tour = await testmodels.UUIDPkModel.create()
        await testmodels.UUIDFkRelatedModel.create(model=tour)

    async def test_instantiated_iterate(self):
        tour = await testmodels.UUIDPkModel.create()
        async for _ in tour.children:
            pass

    async def test_instantiated_await(self):
        tour = await testmodels.UUIDPkModel.create()
        await tour.children

    async def test_minimal__fetched_contains(self):
        tour = await testmodels.UUIDPkModel.create()
        rel = await testmodels.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertTrue(rel in tour.children)

    async def test_minimal__fetched_iter(self):
        tour = await testmodels.UUIDPkModel.create()
        rel = await testmodels.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertEqual([obj for obj in tour.children], [rel])

    async def test_minimal__fetched_len(self):
        tour = await testmodels.UUIDPkModel.create()
        await testmodels.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertEqual(len(tour.children), 1)

    async def test_minimal__fetched_bool(self):
        tour = await testmodels.UUIDPkModel.create()
        await tour.fetch_related("children")
        self.assertFalse(bool(tour.children))
        await testmodels.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertTrue(bool(tour.children))

    async def test_minimal__fetched_getitem(self):
        tour = await testmodels.UUIDPkModel.create()
        rel = await testmodels.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertEqual(tour.children[0], rel)

        with self.assertRaises(IndexError):
            tour.children[1]  # pylint: disable=W0104

    async def test_event__filter(self):
        tour = await testmodels.UUIDPkModel.create()
        event1 = await testmodels.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await testmodels.UUIDFkRelatedModel.create(name="Event2", model=tour)
        self.assertEqual(await tour.children.filter(name="Event1"), [event1])
        self.assertEqual(await tour.children.filter(name="Event2"), [event2])
        self.assertEqual(await tour.children.filter(name="Event3"), [])

    async def test_event__all(self):
        tour = await testmodels.UUIDPkModel.create()
        event1 = await testmodels.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await testmodels.UUIDFkRelatedModel.create(name="Event2", model=tour)
        self.assertSetEqual(set(await tour.children.all()), {event1, event2})

    async def test_event__order_by(self):
        tour = await testmodels.UUIDPkModel.create()
        event1 = await testmodels.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await testmodels.UUIDFkRelatedModel.create(name="Event2", model=tour)
        self.assertEqual(await tour.children.order_by("-name"), [event2, event1])
        self.assertEqual(await tour.children.order_by("name"), [event1, event2])

    async def test_event__limit(self):
        tour = await testmodels.UUIDPkModel.create()
        event1 = await testmodels.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await testmodels.UUIDFkRelatedModel.create(name="Event2", model=tour)
        await testmodels.UUIDFkRelatedModel.create(name="Event3", model=tour)
        self.assertEqual(await tour.children.limit(2).order_by("name"), [event1, event2])

    async def test_event__offset(self):
        tour = await testmodels.UUIDPkModel.create()
        await testmodels.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await testmodels.UUIDFkRelatedModel.create(name="Event2", model=tour)
        event3 = await testmodels.UUIDFkRelatedModel.create(name="Event3", model=tour)
        self.assertEqual(await tour.children.offset(1).order_by("name"), [event2, event3])
