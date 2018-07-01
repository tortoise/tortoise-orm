import sqlite3
import unittest

import asynctest

from tortoise.contrib.testing import TestCase
from tortoise.tests.testmodels import Event


class TestTransactions(TestCase):

    @unittest.expectedFailure
    @asynctest.strict
    async def test_transactions(self):
        try:
            async with self.db.in_transaction() as connection:
                event = Event(name='Test')
                await event.save(using_db=connection)
                await Event.filter(id=event.id).using_db(connection).update(name='Updated name')
                saved_event = await Event.filter(name='Updated name').using_db(connection).first()
                assert saved_event.id == event.id
                await connection.execute_query('SELECT * FROM non_existent_table')
        except sqlite3.OperationalError:
            pass
        saved_event = await Event.filter(name='Updated name').first()
        assert not saved_event
