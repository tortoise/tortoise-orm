from tortoise.contrib import test
from tortoise.tests.testmodels import SourceFields


class TestRelations(test.TestCase):
    async def test_get_all(self):
        obj1 = await SourceFields.create(chars="aaa")
        self.assertIsNotNone(obj1.id, str(dir(obj1)))
        obj2 = await SourceFields.create(chars="bbb")

        objs = await SourceFields.all()
        self.assertEqual(objs, [obj1, obj2])

    async def test_get_by_pk(self):
        obj = await SourceFields.create(chars="aaa")
        obj1 = await SourceFields.get(id=obj.id)

        self.assertEqual(obj, obj1)

    async def test_get_by_chars(self):
        obj = await SourceFields.create(chars="aaa")
        obj1 = await SourceFields.get(chars="aaa")

        self.assertEqual(obj, obj1)
