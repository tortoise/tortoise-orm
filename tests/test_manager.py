from tests.testmodels import ManagerModel, ManagerModelExtra
from tortoise.contrib import test


class TestManager(test.TestCase):
    async def test_manager(self):
        m1 = await ManagerModel.create()
        m2 = await ManagerModel.create(status=1)

        self.assertEqual(await ManagerModel.all().active().count(), 1)
        self.assertEqual(await ManagerModel.all_objects.count(), 2)

        self.assertIsNone(await ManagerModel.all().active().get_or_none(pk=m1.pk))
        self.assertIsNotNone(await ManagerModel.all_objects.get_or_none(pk=m1.pk))
        self.assertIsNotNone(await ManagerModel.get_or_none(pk=m2.pk))

        await ManagerModelExtra.create(extra="extra")
        self.assertEqual(await ManagerModelExtra.all_objects.count(), 1)
        self.assertEqual(await ManagerModelExtra.all().count(), 1)
