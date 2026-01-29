from tests import testmodels
from tortoise.contrib import test
from tortoise.exceptions import (
    IntegrityError,
    NoValuesFetched,
    OperationalError,
    ValidationError,
)
from tortoise.queryset import QuerySet


class TestForeignKeyField(test.TestCase):
    def assertRaisesWrongTypeException(self, relation_name: str):
        return self.assertRaisesRegex(
            ValidationError, f"Invalid type for relationship field '{relation_name}'"
        )

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

    async def test_minimal__by_name__created_prefetched(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        self.assertEqual(rel.tournament, tour)
        self.assertEqual((await tour.minrelations.all())[0], rel)

    async def test_minimal__by_name__unfetched(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        rel = await testmodels.MinRelation.get(id=rel.id)
        self.assertIsInstance(rel.tournament, QuerySet)

    async def test_minimal__by_name__re_awaited(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        await rel.fetch_related("tournament")
        self.assertEqual(rel.tournament, tour)
        self.assertEqual(await rel.tournament, tour)

    async def test_minimal__by_name__awaited(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        rel = await testmodels.MinRelation.get(id=rel.id)
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

    async def test_update_by_name(self):
        tour = await testmodels.Tournament.create(name="Team1")
        tour2 = await testmodels.Tournament.create(name="Team2")
        rel0 = await testmodels.Event.create(name="Event1", tournament=tour)

        await testmodels.Event.filter(pk=rel0.pk).update(tournament=tour2)
        rel = await testmodels.Event.get(event_id=rel0.event_id)

        await rel.fetch_related("tournament")
        self.assertEqual(rel.tournament, tour2)
        self.assertEqual(await tour.events.all(), [])
        self.assertEqual((await tour2.events.all())[0], rel)

    async def test_update_by_id(self):
        tour = await testmodels.Tournament.create(name="Team1")
        tour2 = await testmodels.Tournament.create(name="Team2")
        rel0 = await testmodels.Event.create(name="Event1", tournament_id=tour.id)

        await testmodels.Event.filter(event_id=rel0.event_id).update(tournament_id=tour2.id)
        rel = await testmodels.Event.get(pk=rel0.pk)

        self.assertEqual(rel.tournament_id, tour2.id)
        self.assertEqual(await tour.events.all(), [])
        self.assertEqual((await tour2.events.all())[0], rel)

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
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            "a" in tour.minrelations  # pylint: disable=W0104

    async def test_minimal__unfetched_iter(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            for _ in tour.minrelations:
                pass

    async def test_minimal__unfetched_len(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            len(tour.minrelations)

    async def test_minimal__unfetched_bool(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            bool(tour.minrelations)

    async def test_minimal__unfetched_getitem(self):
        tour = await testmodels.Tournament.create(name="Team1")
        with self.assertRaisesRegex(
            NoValuesFetched,
            "No values were fetched for this relation, first use .fetch_related()",
        ):
            tour.minrelations[0]  # pylint: disable=W0104

    async def test_minimal__instantiated_create(self):
        tour = await testmodels.Tournament.create(name="Team1")
        await testmodels.MinRelation.create(tournament=tour)

    async def test_minimal__instantiated_create_wrong_type(self):
        author = await testmodels.Author.create(name="Author1")
        with self.assertRaisesWrongTypeException("tournament"):
            await testmodels.MinRelation.create(tournament=author)

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
        self.assertEqual(list(tour.minrelations), [rel])

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

    async def test_fk_correct_type_assignment(self):
        tour1 = await testmodels.Tournament.create(name="Team1")
        tour2 = await testmodels.Tournament.create(name="Team2")
        event = await testmodels.Event(name="Event1", tournament=tour1)

        event.tournament = tour2
        await event.save()
        self.assertEqual(event.tournament_id, tour2.id)

    async def test_fk_wrong_type_assignment(self):
        tour = await testmodels.Tournament.create(name="Team1")
        author = await testmodels.Author.create(name="Author")
        rel = await testmodels.MinRelation.create(tournament=tour)

        with self.assertRaisesWrongTypeException("tournament"):
            rel.tournament = author

    async def test_fk_none_assignment(self):
        manager = await testmodels.Employee.create(name="Manager")
        employee = await testmodels.Employee.create(name="Employee", manager=manager)

        employee.manager = None
        await employee.save()
        self.assertIsNone(employee.manager)

    async def test_fk_update_wrong_type(self):
        tour = await testmodels.Tournament.create(name="Team1")
        rel = await testmodels.MinRelation.create(tournament=tour)
        author = await testmodels.Author.create(name="Author1")

        with self.assertRaisesWrongTypeException("tournament"):
            await testmodels.MinRelation.filter(id=rel.id).update(tournament=author)

    async def test_fk_bulk_create_wrong_type(self):
        author = await testmodels.Author.create(name="Author")
        with self.assertRaisesWrongTypeException("tournament"):
            await testmodels.MinRelation.bulk_create(
                [testmodels.MinRelation(tournament=author) for _ in range(10)]
            )

    async def test_fk_bulk_update_wrong_type(self):
        tour = await testmodels.Tournament.create(name="Team1")
        await testmodels.MinRelation.bulk_create(
            [testmodels.MinRelation(tournament=tour) for _ in range(1, 10)]
        )
        author = await testmodels.Author.create(name="Author")

        with self.assertRaisesWrongTypeException("tournament"):
            relations = await testmodels.MinRelation.all()
            await testmodels.MinRelation.bulk_update(
                [testmodels.MinRelation(id=rel.id, tournament=author) for rel in relations],
                fields=["tournament"],
            )
