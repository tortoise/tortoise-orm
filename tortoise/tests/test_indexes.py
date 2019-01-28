import re

from tortoise import Tortoise
from tortoise.contrib import test


class TestFieldIndex(test.TestCase):

    async def setUp(self):
        self.db = Tortoise.get_connection('models')

    async def test_index_created(self):
        explain = {
            'sqlite': 'EXPLAIN QUERY PLAN SELECT * FROM tournament ',
            'postgresql': 'EXPLAIN SELECT * FROM tournament ',
            'mysql': 'EXPLAIN SELECT * FROM `tournament` ',
        }[self.db.database]
        query = explain + "WHERE created BETWEEN '2018-12-20' AND '2018-12-31';"

        plan: dict = (await self.db.execute_query(query))[0]

        self.assertIsNotNone(re.search(
            r'tournament_created_\w+_idx',
            plan['detail'],
        ))
