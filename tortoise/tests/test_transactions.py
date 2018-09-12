from tortoise.contrib import test
from tortoise.exceptions import OperationalError, TransactionManagementError
from tortoise.tests.testmodels import Event, Team, Tournament
from tortoise.transactions import atomic, in_transaction, start_transaction


class SomeException(Exception):
    """
    A very specific exception so s to not accidentally catch another exception.
    """
    pass


@atomic()
async def atomic_decorated_func():
    tournament = Tournament(name='Test')
    await tournament.save()
    return tournament


class TestTransactions(test.IsolatedTestCase):

    async def test_transactions(self):
        with self.assertRaises(SomeException):
            async with in_transaction():
                tournament = Tournament(name='Test')
                await tournament.save()
                await Tournament.filter(id=tournament.id).update(name='Updated name')
                saved_event = await Tournament.filter(name='Updated name').first()
                self.assertEqual(saved_event.id, tournament.id)
                raise SomeException('Some error')

        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertIsNone(saved_event)

    async def test_nested_transactions(self):
        async with in_transaction():
            tournament = Tournament(name='Test')
            await tournament.save()
            await Tournament.filter(id=tournament.id).update(name='Updated name')
            saved_event = await Tournament.filter(name='Updated name').first()
            self.assertEqual(saved_event.id, tournament.id)
            with self.assertRaises(SomeException):
                async with in_transaction():
                    tournament = await Tournament.create(name='Nested')
                    saved_tournament = await Tournament.filter(name='Nested').first()
                    self.assertEqual(tournament.id, saved_tournament.id)
                    raise SomeException('Some error')

        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertIsNotNone(saved_event)
        not_saved_event = await Tournament.filter(name='Nested').first()
        self.assertIsNone(not_saved_event)

    async def test_transaction_decorator(self):
        @atomic()
        async def bound_to_succeed():
            tournament = Tournament(name='Test')
            await tournament.save()
            await Tournament.filter(id=tournament.id).update(name='Updated name')
            saved_event = await Tournament.filter(name='Updated name').first()
            self.assertEqual(saved_event.id, tournament.id)
            return tournament

        tournament = await bound_to_succeed()
        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertEqual(saved_event.id, tournament.id)

    async def test_transaction_decorator_defined_before_init(self):
        tournament = await atomic_decorated_func()
        saved_event = await Tournament.filter(name='Test').first()
        self.assertEqual(saved_event.id, tournament.id)

    async def test_transaction_decorator_fail(self):
        tournament = await Tournament.create(name='Test')

        @atomic()
        async def bound_to_fall():
            await Tournament.filter(id=tournament.id).update(name='Updated name')
            saved_event = await Tournament.filter(name='Updated name').first()
            self.assertEqual(saved_event.id, tournament.id)
            raise OperationalError()

        with self.assertRaises(OperationalError):
            await bound_to_fall()
        saved_event = await Tournament.filter(name='Test').first()
        self.assertEqual(saved_event.id, tournament.id)
        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertIsNone(saved_event)

    async def test_transaction_manual_commit(self):
        tournament = await Tournament.create(name='Test')

        connection = await start_transaction()
        await Tournament.filter(id=tournament.id).update(name='Updated name')
        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertEqual(saved_event.id, tournament.id)
        await connection.commit()

        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertEqual(saved_event.id, tournament.id)

    async def test_transaction_manual_rollback(self):
        tournament = await Tournament.create(name='Test')

        connection = await start_transaction()
        await Tournament.filter(id=tournament.id).update(name='Updated name')
        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertEqual(saved_event.id, tournament.id)
        await connection.rollback()

        saved_event = await Tournament.filter(name='Test').first()
        self.assertEqual(saved_event.id, tournament.id)
        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertIsNone(saved_event)

    async def test_transaction_with_m2m_relations(self):
        async with in_transaction():
            tournament = await Tournament.create(name='Test')
            event = await Event.create(name='Test event', tournament=tournament)
            team = await Team.create(name='Test team')
            await event.participants.add(team)

    async def test_transaction_exception_1(self):
        connection = await start_transaction()
        await connection.rollback()
        with self.assertRaises(TransactionManagementError):
            await connection.rollback()

    async def test_transaction_exception_2(self):
        with self.assertRaises(TransactionManagementError):
            async with in_transaction() as connection:
                await connection.rollback()

    async def test_transaction_exception_3(self):
        connection = await start_transaction()
        await connection.commit()
        with self.assertRaises(TransactionManagementError):
            await connection.commit()

    async def test_transaction_exception_4(self):
        with self.assertRaises(TransactionManagementError):
            async with in_transaction() as connection:
                await connection.commit()
