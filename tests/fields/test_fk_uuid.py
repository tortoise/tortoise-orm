from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError, NoValuesFetched, OperationalError
from tortoise.queryset import QuerySet


class TestForeignKeyUUIDField(test.TestCase):
    """
    Here we do the same FK tests but using UUID. The reason this is useful is:

    * UUID needs escaping, so a good indicator of where we may have missed it.
    * UUID populates a value BEFORE it gets committed to DB, whereas int is AFTER.
    * UUID is stored differently for different DB backends. (native in PG)
    """

    UUIDPkModel = testmodels.UUIDPkModel
    UUIDFkRelatedModel = testmodels.UUIDFkRelatedModel
    UUIDFkRelatedNullModel = testmodels.UUIDFkRelatedNullModel

    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await self.UUIDFkRelatedModel.create()

    async def test_empty_null(self):
        await self.UUIDFkRelatedNullModel.create()

    async def test_create_by_id(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model_id=tour.id)
        self.assertEqual(rel.model_id, tour.id)
        self.assertEqual((await tour.children.all())[0], rel)

    async def test_create_by_name(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model=tour)
        await rel.fetch_related("model")
        self.assertEqual(rel.model, tour)
        self.assertEqual((await tour.children.all())[0], rel)

    async def test_by_name__created_prefetched(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model=tour)
        self.assertEqual(rel.model, tour)
        self.assertEqual((await tour.children.all())[0], rel)

    async def test_by_name__unfetched(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model=tour)
        rel = await self.UUIDFkRelatedModel.get(id=rel.id)
        self.assertIsInstance(rel.model, QuerySet)

    async def test_by_name__re_awaited(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model=tour)
        await rel.fetch_related("model")
        self.assertEqual(rel.model, tour)
        self.assertEqual(await rel.model, tour)

    async def test_by_name__awaited(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model=tour)
        rel = await self.UUIDFkRelatedModel.get(id=rel.id)
        self.assertEqual(await rel.model, tour)
        self.assertEqual((await tour.children.all())[0], rel)

    async def test_update_by_name(self):
        tour = await self.UUIDPkModel.create()
        tour2 = await self.UUIDPkModel.create()
        rel0 = await self.UUIDFkRelatedModel.create(model=tour)

        await self.UUIDFkRelatedModel.filter(id=rel0.id).update(model=tour2)
        rel = await self.UUIDFkRelatedModel.get(id=rel0.id)

        await rel.fetch_related("model")
        self.assertEqual(rel.model, tour2)
        self.assertEqual(await tour.children.all(), [])
        self.assertEqual((await tour2.children.all())[0], rel)

    async def test_update_by_id(self):
        tour = await self.UUIDPkModel.create()
        tour2 = await self.UUIDPkModel.create()
        rel0 = await self.UUIDFkRelatedModel.create(model_id=tour.id)

        await self.UUIDFkRelatedModel.filter(id=rel0.id).update(model_id=tour2.id)
        rel = await self.UUIDFkRelatedModel.get(id=rel0.id)

        self.assertEqual(rel.model_id, tour2.id)
        self.assertEqual(await tour.children.all(), [])
        self.assertEqual((await tour2.children.all())[0], rel)

    async def test_uninstantiated_create(self):
        tour = self.UUIDPkModel()
        with self.assertRaisesRegex(OperationalError, "You should first call .save()"):
            await self.UUIDFkRelatedModel.create(model=tour)

    async def test_uninstantiated_iterate(self):
        tour = self.UUIDPkModel()
        with self.assertRaisesRegex(
            OperationalError, "This objects hasn't been instanced, call .save()"
        ):
            async for _ in tour.children:
                pass

    async def test_uninstantiated_await(self):
        tour = self.UUIDPkModel()
        with self.assertRaisesRegex(
            OperationalError, "This objects hasn't been instanced, call .save()"
        ):
            await tour.children

    async def test_unfetched_contains(self):
        tour = await self.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            "a" in tour.children  # pylint: disable=W0104

    async def test_unfetched_iter(self):
        tour = await self.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            for _ in tour.children:
                pass

    async def test_unfetched_len(self):
        tour = await self.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            len(tour.children)

    async def test_unfetched_bool(self):
        tour = await self.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            bool(tour.children)

    async def test_unfetched_getitem(self):
        tour = await self.UUIDPkModel.create()
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            tour.children[0]  # pylint: disable=W0104

    async def test_instantiated_create(self):
        tour = await self.UUIDPkModel.create()
        await self.UUIDFkRelatedModel.create(model=tour)

    async def test_instantiated_iterate(self):
        tour = await self.UUIDPkModel.create()
        async for _ in tour.children:
            pass

    async def test_instantiated_await(self):
        tour = await self.UUIDPkModel.create()
        await tour.children

    async def test_minimal__fetched_contains(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertTrue(rel in tour.children)

    async def test_minimal__fetched_iter(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertEqual(list(tour.children), [rel])

    async def test_minimal__fetched_len(self):
        tour = await self.UUIDPkModel.create()
        await self.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertEqual(len(tour.children), 1)

    async def test_minimal__fetched_bool(self):
        tour = await self.UUIDPkModel.create()
        await tour.fetch_related("children")
        self.assertFalse(bool(tour.children))
        await self.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertTrue(bool(tour.children))

    async def test_minimal__fetched_getitem(self):
        tour = await self.UUIDPkModel.create()
        rel = await self.UUIDFkRelatedModel.create(model=tour)
        await tour.fetch_related("children")
        self.assertEqual(tour.children[0], rel)

        with self.assertRaises(IndexError):
            tour.children[1]  # pylint: disable=W0104

    async def test_event__filter(self):
        tour = await self.UUIDPkModel.create()
        event1 = await self.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await self.UUIDFkRelatedModel.create(name="Event2", model=tour)
        self.assertEqual(await tour.children.filter(name="Event1"), [event1])
        self.assertEqual(await tour.children.filter(name="Event2"), [event2])
        self.assertEqual(await tour.children.filter(name="Event3"), [])

    async def test_event__all(self):
        tour = await self.UUIDPkModel.create()
        event1 = await self.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await self.UUIDFkRelatedModel.create(name="Event2", model=tour)
        self.assertSetEqual(set(await tour.children.all()), {event1, event2})

    async def test_event__order_by(self):
        tour = await self.UUIDPkModel.create()
        event1 = await self.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await self.UUIDFkRelatedModel.create(name="Event2", model=tour)
        self.assertEqual(await tour.children.order_by("-name"), [event2, event1])
        self.assertEqual(await tour.children.order_by("name"), [event1, event2])

    async def test_event__limit(self):
        tour = await self.UUIDPkModel.create()
        event1 = await self.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await self.UUIDFkRelatedModel.create(name="Event2", model=tour)
        await self.UUIDFkRelatedModel.create(name="Event3", model=tour)
        self.assertEqual(await tour.children.limit(2).order_by("name"), [event1, event2])

    async def test_event__offset(self):
        tour = await self.UUIDPkModel.create()
        await self.UUIDFkRelatedModel.create(name="Event1", model=tour)
        event2 = await self.UUIDFkRelatedModel.create(name="Event2", model=tour)
        event3 = await self.UUIDFkRelatedModel.create(name="Event3", model=tour)
        self.assertEqual(await tour.children.offset(1).order_by("name"), [event2, event3])

    async def test_assign_by_id(self):
        tour = await self.UUIDPkModel.create()
        event = await self.UUIDFkRelatedNullModel.create(model=None)
        event.model_id = tour.id
        await event.save()
        event0 = await self.UUIDFkRelatedNullModel.get(id=event.id)
        self.assertEqual(event0.model_id, tour.id)
        await event0.fetch_related("model")
        self.assertEqual(event0.model, tour)

    async def test_assign_by_name(self):
        tour = await self.UUIDPkModel.create()
        event = await self.UUIDFkRelatedNullModel.create(model=None)
        event.model = tour
        await event.save()
        event0 = await self.UUIDFkRelatedNullModel.get(id=event.id)
        self.assertEqual(event0.model_id, tour.id)
        await event0.fetch_related("model")
        self.assertEqual(event0.model, tour)

    async def test_assign_none_by_id(self):
        tour = await self.UUIDPkModel.create()
        event = await self.UUIDFkRelatedNullModel.create(model=tour)
        event.model_id = None
        await event.save()
        event0 = await self.UUIDFkRelatedNullModel.get(id=event.id)
        self.assertEqual(event0.model_id, None)
        await event0.fetch_related("model")
        self.assertEqual(event0.model, None)

    async def test_assign_none_by_name(self):
        tour = await self.UUIDPkModel.create()
        event = await self.UUIDFkRelatedNullModel.create(model=tour)
        event.model = None
        await event.save()
        event0 = await self.UUIDFkRelatedNullModel.get(id=event.id)
        self.assertEqual(event0.model_id, None)
        await event0.fetch_related("model")
        self.assertEqual(event0.model, None)

    async def test_assign_none_by_id_fails(self):
        tour = await self.UUIDPkModel.create()
        event = await self.UUIDFkRelatedModel.create(model=tour)
        event.model_id = None
        with self.assertRaises(IntegrityError):
            await event.save()

    async def test_assign_none_by_name_fails(self):
        tour = await self.UUIDPkModel.create()
        event = await self.UUIDFkRelatedModel.create(model=tour)
        event.model = None
        with self.assertRaises(IntegrityError):
            await event.save()

    async def test_delete_by_name(self):
        tour = await self.UUIDPkModel.create()
        event = await self.UUIDFkRelatedModel.create(model=tour)
        del event.model
        with self.assertRaises(IntegrityError):
            await event.save()


class TestForeignKeyUUIDSourcedField(TestForeignKeyUUIDField):
    """
    Here we test the identical Python-like models, but with all customized DB names.

    This helps test that we don't confuse the two concepts.
    """

    UUIDPkModel = testmodels.UUIDPkSourceModel  # type: ignore
    UUIDFkRelatedModel = testmodels.UUIDFkRelatedSourceModel  # type: ignore
    UUIDFkRelatedNullModel = testmodels.UUIDFkRelatedNullSourceModel  # type: ignore
