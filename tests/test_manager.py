from tests.testmodels import ManagerModel
from tortoise.contrib import test


class TestManager(test.TestCase):
    async def test_manager(self):
        m1 = await ManagerModel.create()
        m2 = await ManagerModel.create(status=1)

        self.assertEqual(await ManagerModel.all().count(), 1)
        self.assertEqual(await ManagerModel.all_objects.count(), 2)

        self.assertIsNone(await ManagerModel.get_or_none(pk=m1.pk))
        self.assertIsNotNone(await ManagerModel.all_objects.get_or_none(pk=m1.pk))
        self.assertIsNotNone(await ManagerModel.get_or_none(pk=m2.pk))
