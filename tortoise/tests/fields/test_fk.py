from tortoise.contrib import test
from tortoise.exceptions import IntegrityError, NoValuesFetched, OperationalError
from tortoise.tests import testmodels


class TestForeignKeyField(test.TestCase):
    async def test_empty(self):
        with self.assertRaises(IntegrityError):
            await testmodels.MinRelation.create()

    async def test_minimal__create_by_id(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament_id=tour.id)
        self.assertEqual(rel.tournament_id, tour.id)
        self.assertEqual((await tour.minrelations.all())[0], rel)

    async def test_minimal__create_by_name(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        await rel.fetch_related("tournament")
        self.assertEqual(rel.tournament, tour)
        self.assertEqual((await tour.minrelations.all())[0], rel)

    @test.skip("Not yet implemented")
    async def test_minimal__by_name__unfetched(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        with self.assertRaisesRegex(NoValuesFetched, "moo"):
            rel.tournament  # pylint: disable=W0104

    @test.skip("Not yet implemented")
    async def test_minimal__by_name__awaited(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        self.assertEqual(await rel.tournament, tour)
        self.assertEqual((await tour.minrelations.all())[0], rel)

    async def test_event__create_by_id(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.Event.create(name="Event1", tournament_id=tour.id)
        self.assertEqual(rel.tournament_id, tour.id)
        self.assertEqual((await tour.events.all())[0], rel)

    async def test_event__create_by_name(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.Event.create(name="Event1", tournament=tour)
        await rel.fetch_related("tournament")
        self.assertEqual(rel.tournament, tour)
        self.assertEqual((await tour.events.all())[0], rel)

    async def test_minimal__uninstantiated_create(self):
        tour = testmodels.Tournament(name="Team1")
        with self.assertRaisesRegex(OperationalError, "You should first call .save()"):
            await testmodels.MinRelation.create(tournament=tour)

    async def test_minimal__uninstantiated_iterate(self):
        tour = testmodels.Tournament(name="Team1")
        with self.assertRaisesRegex(
            OperationalError, "This objects hasn't been instanced, call .save()"
        ):
            async for _ in tour.minrelations:
                pass

    async def test_minimal__uninstantiated_await(self):
        tour = testmodels.Tournament(name="Team1")
        with self.assertRaisesRegex(
            OperationalError, "This objects hasn't been instanced, call .save()"
        ):
            await tour.minrelations

    async def test_minimal__unfetched_contains(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            "a" in tour.minrelations  # pylint: disable=W0104

    async def test_minimal__unfetched_iter(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            for _ in tour.minrelations:
                pass

    async def test_minimal__unfetched_len(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            len(tour.minrelations)

    async def test_minimal__unfetched_bool(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            bool(tour.minrelations)

    async def test_minimal__unfetched_getitem(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation," " first use .fetch_related()",
        ):
            tour.minrelations[0]  # pylint: disable=W0104

    async def test_minimal__instantiated_create(self):
        tour = await testmodels.Tournament.create(name="Team1")
        await testmodels.MinRelation.create(tournament=tour)

    async def test_minimal__instantiated_iterate(self):
        tour = await testmodels.Tournament.create(name="Team1")
        async for _ in tour.minrelations:
            pass

    async def test_minimal__instantiated_await(self):
        tour = await testmodels.Tournament.create(name="Team1")
        await tour.minrelations

    async def test_minimal__fetched_contains(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        await tour.fetch_related("minrelations")
        self.assertTrue(rel in tour.minrelations)

    async def test_minimal__fetched_iter(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        await tour.fetch_related("minrelations")
        self.assertEqual([obj for obj in tour.minrelations], [rel])

    async def test_minimal__fetched_len(self):
        tour = await testmodels.Tournament.create(name="Team1")
        await testmodels.MinRelation.create(tournament=tour)
        await tour.fetch_related("minrelations")
        self.assertEqual(len(tour.minrelations), 1)

    async def test_minimal__fetched_bool(self):
        tour = await testmodels.Tournament.create(name="Team1")
        await tour.fetch_related("minrelations")
        self.assertFalse(bool(tour.minrelations))
        await testmodels.MinRelation.create(tournament=tour)
        await tour.fetch_related("minrelations")
        self.assertTrue(bool(tour.minrelations))

    async def test_minimal__fetched_getitem(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        await tour.fetch_related("minrelations")
        self.assertEqual(tour.minrelations[0], rel)

        with self.assertRaises(IndexError):
            tour.minrelations[1]  # pylint: disable=W0104

    async def test_event__filter(self):
        tour = await testmodels.Tournament.create(name="Team1")
        event1 = await testmodels.Event.create(name="Event1", tournament=tour)
        event2 = await testmodels.Event.create(name="Event2", tournament=tour)
        self.assertEqual(await tour.events.filter(name="Event1"), [event1])
        self.assertEqual(await tour.events.filter(name="Event2"), [event2])
        self.assertEqual(await tour.events.filter(name="Event3"), [])

    async def test_event__all(self):
        tour = await testmodels.Tournament.create(name="Team1")
        event1 = await testmodels.Event.create(name="Event1", tournament=tour)
        event2 = await testmodels.Event.create(name="Event2", tournament=tour)
        self.assertSetEqual(set(await tour.events.all()), {event1, event2})

    async def test_event__order_by(self):
        tour = await testmodels.Tournament.create(name="Team1")
        event1 = await testmodels.Event.create(name="Event1", tournament=tour)
        event2 = await testmodels.Event.create(name="Event2", tournament=tour)
        self.assertEqual(await tour.events.order_by("-name"), [event2, event1])
        self.assertEqual(await tour.events.order_by("name"), [event1, event2])

    async def test_event__limit(self):
        tour = await testmodels.Tournament.create(name="Team1")
        event1 = await testmodels.Event.create(name="Event1", tournament=tour)
        event2 = await testmodels.Event.create(name="Event2", tournament=tour)
        await testmodels.Event.create(name="Event3", tournament=tour)
        self.assertEqual(await tour.events.limit(2).order_by("name"), [event1, event2])

    async def test_event__offset(self):
        tour = await testmodels.Tournament.create(name="Team1")
        await testmodels.Event.create(name="Event1", tournament=tour)
        event2 = await testmodels.Event.create(name="Event2", tournament=tour)
        event3 = await testmodels.Event.create(name="Event3", tournament=tour)
        self.assertEqual(await tour.events.offset(1).order_by("name"), [event2, event3])
