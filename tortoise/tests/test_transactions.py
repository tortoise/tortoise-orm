from tortoise.contrib.test import TestCase
from tortoise.exceptions import OperationalError
from tortoise.tests.testmodels import Tournament


class TestTransactions(TestCase):

    async def test_transactions(self):
        with self.assertRaises(OperationalError):
            async with self.db.in_transaction() as connection:
                event = Tournament(name='Test')
                await event.save(using_db=connection)
                await Tournament.filter(id=event.id).using_db(
                    connection).update(name='Updated name')
                saved_event = await Tournament.filter(
                    name='Updated name').using_db(connection).first()
                self.assertEqual(saved_event.id, event.id)
                await connection.execute_query('SELECT * FROM non_existent_table')

        saved_event = await Tournament.filter(name='Updated name').first()
        self.assertIsNone(saved_event)
