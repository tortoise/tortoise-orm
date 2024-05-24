from uuid import UUID, uuid4

from tests.testmodels import UniqueName, UUIDPkModel
from tortoise.contrib import test
from tortoise.contrib.test.condition import NotEQ
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction


class TestBulk(test.TruncationTestCase):
    async def test_bulk_create(self):
        await UniqueName.bulk_create([UniqueName() for _ in range(1000)])
        all_ = await UniqueName.all().values("id", "name")
        inc = all_[0]["id"]
        self.assertListSortEqual(
            all_,
            [{"id": val + inc, "name": None} for val in range(1000)],
            sorted_key="id",
        )

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_bulk_create_update_fields(self):
        await UniqueName.bulk_create([UniqueName(name="name")])
        await UniqueName.bulk_create(
            [UniqueName(name="name", optional="optional")],
            update_fields=["optional"],
            on_conflict=["name"],
        )
        all_ = await UniqueName.all().values("name", "optional")
        self.assertListSortEqual(all_, [{"name": "name", "optional": "optional"}])

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_bulk_create_more_that_one_update_fields(self):
        await UniqueName.bulk_create([UniqueName(name="name")])
        await UniqueName.bulk_create(
            [UniqueName(name="name", optional="optional", other_optional="other_optional")],
            update_fields=["optional", "other_optional"],
            on_conflict=["name"],
        )
        all_ = await UniqueName.all().values("name", "optional", "other_optional")
        self.assertListSortEqual(
            all_,
            [
                {
                    "name": "name",
                    "optional": "optional",
                    "other_optional": "other_optional",
                }
            ],
        )

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_bulk_create_with_batch_size(self):
        await UniqueName.bulk_create(
            [UniqueName(id=id_ + 1) for id_ in range(1000)], batch_size=100
        )
        all_ = await UniqueName.all().values("id", "name")
        self.assertListSortEqual(
            all_,
            [{"id": val + 1, "name": None} for val in range(1000)],
            sorted_key="id",
        )

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_bulk_create_with_specified(self):
        await UniqueName.bulk_create([UniqueName(id=id_) for id_ in range(1000, 2000)])
        all_ = await UniqueName.all().values("id", "name")
        self.assertListSortEqual(
            all_,
            [{"id": id_, "name": None} for id_ in range(1000, 2000)],
            sorted_key="id",
        )

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_bulk_create_mix_specified(self):
        predefined_start = 40000
        predefined_end = 40150
        undefined_count = 100

        await UniqueName.bulk_create(
            [UniqueName(id=id_) for id_ in range(predefined_start, predefined_end)]
            + [UniqueName() for _ in range(undefined_count)]
        )

        all_ = await UniqueName.all().order_by("id").values("id", "name")
        predefined_count = predefined_end - predefined_start
        assert len(all_) == (predefined_count + undefined_count)

        if all_[0]["id"] == predefined_start:
            assert sorted(all_[:predefined_count], key=lambda x: x["id"]) == [
                {"id": id_, "name": None} for id_ in range(predefined_start, predefined_end)
            ]
            inc = all_[predefined_count]["id"]
            assert sorted(all_[predefined_count:], key=lambda x: x["id"]) == [
                {"id": val + inc, "name": None} for val in range(undefined_count)
            ]
        else:
            inc = all_[0]["id"]
            assert sorted(all_[:undefined_count], key=lambda x: x["id"]) == [
                {"id": val + inc, "name": None} for val in range(undefined_count)
            ]
            assert sorted(all_[undefined_count:], key=lambda x: x["id"]) == [
                {"id": id_, "name": None} for id_ in range(predefined_start, predefined_end)
            ]

    async def test_bulk_create_uuidpk(self):
        await UUIDPkModel.bulk_create([UUIDPkModel() for _ in range(1000)])
        res = await UUIDPkModel.all().values_list("id", flat=True)
        self.assertEqual(len(res), 1000)
        self.assertIsInstance(res[0], UUID)

    @test.requireCapability(supports_transactions=True)
    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_bulk_create_in_transaction(self):
        async with in_transaction():
            await UniqueName.bulk_create([UniqueName() for _ in range(1000)])
        all_ = await UniqueName.all().order_by("id").values("id", "name")
        inc = all_[0]["id"]
        self.assertEqual(all_, [{"id": val + inc, "name": None} for val in range(1000)])

    @test.requireCapability(supports_transactions=True)
    async def test_bulk_create_uuidpk_in_transaction(self):
        async with in_transaction():
            await UUIDPkModel.bulk_create([UUIDPkModel() for _ in range(1000)])
        res = await UUIDPkModel.all().values_list("id", flat=True)
        self.assertEqual(len(res), 1000)
        self.assertIsInstance(res[0], UUID)

    @test.requireCapability(dialect=NotEQ("mssql"))
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

    @test.requireCapability(supports_transactions=True, dialect=NotEQ("mssql"))
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

    @test.requireCapability(dialect=NotEQ("mssql"))
    async def test_bulk_create_ignore_conflicts(self):
        name1 = UniqueName(name="name1")
        name2 = UniqueName(name="name2")
        await UniqueName.bulk_create([name1, name2])
        await UniqueName.bulk_create([name1, name2], ignore_conflicts=True)
        with self.assertRaises(IntegrityError):
            await UniqueName.bulk_create([name1, name2])
