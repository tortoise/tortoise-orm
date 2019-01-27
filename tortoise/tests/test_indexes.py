import re

from tortoise import Tortoise
from tortoise.contrib import test


class TestFieldIndex(test.TestCase):

    async def setUp(self):
        self.db = Tortoise.get_connection('models')

    async def test_index_created(self):
        # NOTE: this is only valid because the test database is an SQLite one.
        plan: dict = (await self.db.execute_query(
            'EXPLAIN QUERY PLAN SELECT * FROM tournament '
            'WHERE created BETWEEN "12/20/2018" AND "12/31/2018";'
        ))[0]
        self.assertIsNotNone(re.search(
            r"USING INDEX tournament_created_\w+_idx",
            plan["detail"],
        ))
