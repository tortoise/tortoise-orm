from collections.abc import Iterable

import pytest

from tests.testmodels import UniqueName
from tortoise.contrib.test import requireCapability
from tortoise.contrib.test.condition import NotEQ


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
@pytest.mark.parametrize("iterator_option", ["update_fields", "on_conflict", "both"])
@pytest.mark.parametrize("preview", [False, True])
async def test_bulk_create_preserves_field_iterators(db, iterator_option, preview):
    existing = await UniqueName.create(name="existing", optional="old", other_optional="keep")
    update_fields: Iterable[str] = ["optional"]
    on_conflict: Iterable[str] = ["name"]
    if iterator_option in ("update_fields", "both"):
        update_fields = iter(update_fields)
    if iterator_option in ("on_conflict", "both"):
        on_conflict = iter(on_conflict)
    objects = [
        UniqueName(id=existing.id, name="existing", optional="updated", other_optional="replace"),
        UniqueName(name="new", optional="inserted"),
    ]
    query = UniqueName.bulk_create(
        iter(objects), batch_size=1, update_fields=update_fields, on_conflict=on_conflict
    )

    if preview:
        assert query.sql() == query.sql()
        assert await UniqueName.all().values("name", "optional") == [
            {"name": "existing", "optional": "old"}
        ]
    await query

    assert await UniqueName.all().order_by("name").values("name", "optional", "other_optional") == [
        {"name": "existing", "optional": "updated", "other_optional": "keep"},
        {"name": "new", "optional": "inserted", "other_optional": None},
    ]


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
@pytest.mark.parametrize("field_type", [list, tuple])
async def test_bulk_create_repeatable_sql_with_field_sequences(db, field_type):
    await UniqueName.create(name="existing", optional="old")
    query = UniqueName.bulk_create(
        [UniqueName(name="existing", optional="updated")],
        update_fields=field_type(["optional"]),
        on_conflict=field_type(["name"]),
    )

    assert query.sql() == query.sql()
    await query

    assert await UniqueName.all().values("name", "optional") == [
        {"name": "existing", "optional": "updated"}
    ]


@pytest.mark.parametrize("empty_option", ["update_fields", "on_conflict"])
def test_bulk_create_validates_empty_field_iterators(db, empty_option):
    update_fields = iter(()) if empty_option == "update_fields" else ["optional"]
    on_conflict = iter(()) if empty_option == "on_conflict" else ["name"]

    with pytest.raises(ValueError, match="update_fields and on_conflict"):
        UniqueName.bulk_create(
            [UniqueName(name="new")], update_fields=update_fields, on_conflict=on_conflict
        )


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_allows_empty_field_iterators(db):
    await UniqueName.bulk_create(
        [UniqueName(name="new")], update_fields=iter(()), on_conflict=iter(())
    )

    assert await UniqueName.all().values_list("name", flat=True) == ["new"]


@requireCapability(dialect=NotEQ("mssql"))
@pytest.mark.asyncio
async def test_bulk_create_ignore_conflicts_allows_empty_update_iterator(db):
    await UniqueName.create(name="existing", optional="old")

    await UniqueName.bulk_create(
        [UniqueName(name="existing", optional="updated")],
        ignore_conflicts=True,
        update_fields=iter(()),
    )

    assert await UniqueName.all().values("name", "optional") == [
        {"name": "existing", "optional": "old"}
    ]
