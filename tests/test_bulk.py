from uuid import UUID

from tests.testmodels import NoID, UUIDPkModel
from tortoise.contrib import test


class TestBasic(test.TestCase):
    async def test_bulk_create(self):
        await NoID.bulk_create([NoID() for _ in range(1, 1000)])
        self.assertEqual(
            await NoID.all().values("id", "name"),
            [{"id": val, "name": None} for val in range(1, 1000)],
        )

    async def test_bulk_create_uuidpk(self):
        await UUIDPkModel.bulk_create([UUIDPkModel() for _ in range(1000)])
        res = await UUIDPkModel.all().values_list("id", flat=True)
        self.assertEqual(len(res), 1000)
        self.assertIsInstance(res[0], UUID)
