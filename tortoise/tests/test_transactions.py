import sqlite3

import asynctest

from tortoise.contrib.testing import TestCase
from tortoise.tests.testmodels import Tournament


class TestTransactions(TestCase):

    @asynctest.strict
    async def test_transactions(self):
        try:
            async with self.db.in_transaction() as connection:
                event = Tournament(name='Test')
                await event.save(using_db=connection)
                await Tournament.filter(id=event.id).using_db(connection).update(name='Updated name')
                saved_event = await Tournament.filter(name='Updated name').using_db(connection).first()
                assert saved_event.id == event.id
                await connection.execute_query('SELECT * FROM non_existent_table')
        except sqlite3.OperationalError:
            pass
        saved_event = await Tournament.filter(name='Updated name').first()
        assert not saved_event
