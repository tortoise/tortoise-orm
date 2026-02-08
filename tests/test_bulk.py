from uuid import UUID, uuid4

import pytest

from tests.testmodels import UniqueName, UUIDPkModel
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotEQ
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction


def assert_list_sort_equal(actual, expected, sorted_key="id"):
    """Assert two lists are equal after sorting by the given key."""
    assert sorted(actual, key=lambda x: x[sorted_key]) == sorted(
        expected, key=lambda x: x[sorted_key]
    )


@pytest.mark.asyncio
async def test_bulk_create(db_truncate):
    """Test basic bulk create operation."""
    await UniqueName.bulk_create([UniqueName() for _ in range(1000)])
    all_ = await UniqueName.all().values("id", "name")
    inc = all_[0]["id"]
    assert_list_sort_equal(
        all_,
        [{"id": val + inc, "name": None} for val in range(1000)],
        sorted_key="id",
    )


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_update_fields(db_truncate):
    """Test bulk create with update_fields on conflict."""
    await UniqueName.bulk_create([UniqueName(name="name")])
    await UniqueName.bulk_create(
        [UniqueName(name="name", optional="optional")],
        update_fields=["optional"],
        on_conflict=["name"],
    )
    all_ = await UniqueName.all().values("name", "optional")
    assert all_ == [{"name": "name", "optional": "optional"}]


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_more_that_one_update_fields(db_truncate):
    """Test bulk create with multiple update_fields on conflict."""
    await UniqueName.bulk_create([UniqueName(name="name")])
    await UniqueName.bulk_create(
        [UniqueName(name="name", optional="optional", other_optional="other_optional")],
        update_fields=["optional", "other_optional"],
        on_conflict=["name"],
    )
    all_ = await UniqueName.all().values("name", "optional", "other_optional")
    assert all_ == [
        {
            "name": "name",
            "optional": "optional",
            "other_optional": "other_optional",
        }
    ]


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_with_batch_size(db_truncate):
    """Test bulk create with batch_size parameter."""
    await UniqueName.bulk_create([UniqueName(id=id_ + 1) for id_ in range(1000)], batch_size=100)
    all_ = await UniqueName.all().values("id", "name")
    assert_list_sort_equal(
        all_,
        [{"id": val + 1, "name": None} for val in range(1000)],
        sorted_key="id",
    )


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_with_specified(db_truncate):
    """Test bulk create with specified IDs."""
    await UniqueName.bulk_create([UniqueName(id=id_) for id_ in range(1000, 2000)])
    all_ = await UniqueName.all().values("id", "name")
    assert_list_sort_equal(
        all_,
        [{"id": id_, "name": None} for id_ in range(1000, 2000)],
        sorted_key="id",
    )


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_mix_specified(db_truncate):
    """Test bulk create with mix of specified and auto-generated IDs."""
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


@pytest.mark.asyncio
async def test_bulk_create_uuidpk(db_truncate):
    """Test bulk create with UUID primary key model."""
    await UUIDPkModel.bulk_create([UUIDPkModel() for _ in range(1000)])
    res = await UUIDPkModel.all().values_list("id", flat=True)
    assert len(res) == 1000
    assert isinstance(res[0], UUID)


@requireCapability(supports_transactions=True)
@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_in_transaction(db_truncate):
    """Test bulk create inside transaction."""
    async with in_transaction():
        await UniqueName.bulk_create([UniqueName() for _ in range(1000)])
    all_ = await UniqueName.all().order_by("id").values("id", "name")
    inc = all_[0]["id"]
    assert all_ == [{"id": val + inc, "name": None} for val in range(1000)]


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_bulk_create_uuidpk_in_transaction(db_truncate):
    """Test bulk create with UUID PK inside transaction."""
    async with in_transaction():
        await UUIDPkModel.bulk_create([UUIDPkModel() for _ in range(1000)])
    res = await UUIDPkModel.all().values_list("id", flat=True)
    assert len(res) == 1000
    assert isinstance(res[0], UUID)


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_fail(db_truncate):
    """Test bulk create fails with duplicate names."""
    with pytest.raises(IntegrityError):
        await UniqueName.bulk_create(
            [UniqueName(name=str(i)) for i in range(10)]
            + [UniqueName(name=str(i)) for i in range(10)]
        )


@pytest.mark.asyncio
async def test_bulk_create_uuidpk_fail(db_truncate):
    """Test bulk create fails with duplicate UUID PKs."""
    val = uuid4()
    with pytest.raises(IntegrityError):
        await UUIDPkModel.bulk_create([UUIDPkModel(id=val) for _ in range(10)])


@requireCapability(supports_transactions=True, dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_in_transaction_fail(db_truncate):
    """Test bulk create fails inside transaction with duplicates."""
    with pytest.raises(IntegrityError):
        async with in_transaction():
            await UniqueName.bulk_create(
                [UniqueName(name=str(i)) for i in range(10)]
                + [UniqueName(name=str(i)) for i in range(10)]
            )


@requireCapability(supports_transactions=True)
@pytest.mark.asyncio
async def test_bulk_create_uuidpk_in_transaction_fail(db_truncate):
    """Test bulk create with UUID PK fails in transaction with duplicates."""
    val = uuid4()
    with pytest.raises(IntegrityError):
        async with in_transaction():
            await UUIDPkModel.bulk_create([UUIDPkModel(id=val) for _ in range(10)])


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_ignore_conflicts(db_truncate):
    """Test bulk create with ignore_conflicts option."""
    name1 = UniqueName(name="name1")
    name2 = UniqueName(name="name2")
    await UniqueName.bulk_create([name1, name2])
    await UniqueName.bulk_create([name1, name2], ignore_conflicts=True)
    with pytest.raises(IntegrityError):
        await UniqueName.bulk_create([name1, name2])
