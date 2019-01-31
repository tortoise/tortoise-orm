import re
from datetime import datetime

from tortoise.contrib import test
from tortoise.tests.testmodels import Tournament


class TestFieldIndex(test.TestCase):
    async def test_index_created(self):
        # The database *should* use the index on `created` when filtering on it.
        plan = await Tournament.filter(created__lt=datetime.now()).explain()
        self.assertIsNotNone(re.search(r'tournament_created_\w+_idx', str(plan)))
