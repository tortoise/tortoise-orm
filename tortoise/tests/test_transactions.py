from tortoise.contrib import test
from tortoise.exceptions import OperationalError
from tortoise.tests.testmodels import Tournament
from tortoise.transactions import atomic, in_transaction


class TestTransactions(test.IsolatedTestCase):

    async def test_transactions(self):
        with self.assertRaises(OperationalError):
            async with in_transaction() as connection:
                tournament = Tournament(name='Test')
                await tournament.save()
                await Tournament.filter(id=tournament.id).update(name='Updated name')
                saved_event = await Tournament.filter(name='Updated name').first()
                self.assertEqual(saved_event.id, tournament.id)
                await connection.execute_query('SELECT * FROM non_existent_table')

        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertIsNone(saved_event)

    async def test_nested_transactions(self):
        async with in_transaction():
            tournament = Tournament(name='Test')
            await tournament.save()
            await Tournament.filter(id=tournament.id).update(name='Updated name')
            saved_event = await Tournament.filter(name='Updated name').first()
            self.assertEqual(saved_event.id, tournament.id)
            with self.assertRaises(OperationalError):
                async with in_transaction() as connection:
                    tournament = await Tournament.create(name='Nested')
                    saved_tournament = await Tournament.filter(name='Nested').first()
                    self.assertEqual(tournament.id, saved_tournament.id)
                    await connection.execute_query('SELECT * FROM non_existent_table')

        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertIsNotNone(saved_event)
        not_saved_event = await Tournament.filter(name='Nested').first()
        self.assertIsNone(not_saved_event)

    async def test_transaction_decorator(self):
        @atomic()
        async def bound_to_fall():
            tournament = Tournament(name='Test')
            await tournament.save()
            await Tournament.filter(id=tournament.id).update(name='Updated name')
            saved_event = await Tournament.filter(name='Updated name').first()
            self.assertEqual(saved_event.id, tournament.id)
            raise OperationalError()

        with self.assertRaises(OperationalError):
            await bound_to_fall()
        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertIsNone(saved_event)
