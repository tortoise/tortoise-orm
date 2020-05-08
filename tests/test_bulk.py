from uuid import UUID, uuid4

from tests.testmodels import UniqueName, UUIDPkModel
from tortoise.contrib import test
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction


class TestBulk(test.TruncationTestCase):
    async def test_bulk_create(self):
        await UniqueName.bulk_create([UniqueName() for _ in range(1000)])
        all_ = await UniqueName.all().values("id", "name")
        inc = all_[0]["id"]
        self.assertEqual(all_, [{"id": val + inc, "name": None} for val in range(1000)])

    async def test_bulk_create_with_specified(self):
        await UniqueName.bulk_create([UniqueName(id=id_) for id_ in range(1000, 2000)])
        all_ = await UniqueName.all().values("id", "name")
        self.assertEqual(all_, [{"id": id_, "name": None} for id_ in range(1000, 2000)])

    async def test_bulk_create_mix_specified(self):
        await UniqueName.bulk_create(
            [UniqueName(id=id_) for id_ in range(10000, 11000)]
            + [UniqueName() for _ in range(1000)]
        )

        all_ = await UniqueName.all().values("id", "name")
        self.assertEqual(len(all_), 2000)

        self.assertEqual(all_[:1000], [{"id": id_, "name": None} for id_ in range(10000, 11000)])
        inc = all_[1000]["id"]
        self.assertEqual(all_[1000:], [{"id": val + inc, "name": None} for val in range(1000)])

    async def test_bulk_create_uuidpk(self):
        await UUIDPkModel.bulk_create([UUIDPkModel() for _ in range(1000)])
        res = await UUIDPkModel.all().values_list("id", flat=True)
        self.assertEqual(len(res), 1000)
        self.assertIsInstance(res[0], UUID)

    @test.requireCapability(supports_transactions=True)
    async def test_bulk_create_in_transaction(self):
        async with in_transaction():
            await UniqueName.bulk_create([UniqueName() for _ in range(1000)])
        all_ = await UniqueName.all().values("id", "name")
        inc = all_[0]["id"]
        self.assertEqual(all_, [{"id": val + inc, "name": None} for val in range(1000)])

    @test.requireCapability(supports_transactions=True)
    async def test_bulk_create_uuidpk_in_transaction(self):
        async with in_transaction():
            await UUIDPkModel.bulk_create([UUIDPkModel() for _ in range(1000)])
        res = await UUIDPkModel.all().values_list("id", flat=True)
        self.assertEqual(len(res), 1000)
        self.assertIsInstance(res[0], UUID)

    async def test_bulk_create_fail(self):
        with self.assertRaises(IntegrityError):
            await UniqueName.bulk_create(
                [UniqueName(name=str(i)) for i in range(10)]
                + [UniqueName(name=str(i)) for i in range(10)]
            )

    async def test_bulk_create_uuidpk_fail(self):
        val = uuid4()
        with self.assertRaises(IntegrityError):
            await UUIDPkModel.bulk_create([UUIDPkModel(id=val) for _ in range(10)])

    @test.requireCapability(supports_transactions=True)
    async def test_bulk_create_in_transaction_fail(self):
        with self.assertRaises(IntegrityError):
            async with in_transaction():
                await UniqueName.bulk_create(
                    [UniqueName(name=str(i)) for i in range(10)]
                    + [UniqueName(name=str(i)) for i in range(10)]
                )

    @test.requireCapability(supports_transactions=True)
    async def test_bulk_create_uuidpk_in_transaction_fail(self):
        val = uuid4()
        with self.assertRaises(IntegrityError):
            async with in_transaction():
                await UUIDPkModel.bulk_create([UUIDPkModel(id=val) for _ in range(10)])
