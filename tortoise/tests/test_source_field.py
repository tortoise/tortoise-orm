from tortoise.contrib import test
from tortoise.tests.testmodels import SourceFields


class TestRelations(test.TestCase):
    async def test_basic(self):
        a_1 = await SourceFields.create(chars="aaa")
        a_2 = await SourceFields.get(id=a_1.id)

        self.assertEqual(a_1, a_2)
