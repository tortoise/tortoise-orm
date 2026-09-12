"""Regression tests for Postgres 63-byte identifier truncation on JOIN aliases.

See https://github.com/tortoise/tortoise-orm/issues/1902
"""

import pytest

from tests.testmodels import (
    LongJoinAuthor,
    LongJoinBook,
    LongJoinChapter,
    LongJoinParent,
    ThisIsAnExcessivelyLongOneToOneChildModelName,
)
from tortoise.backends.base.executor import BaseExecutor


class _IndexRecord:
    """Row that supports positional access like an asyncpg Record."""

    def __init__(self, keys: list[str], values: list[object]) -> None:
        self._keys = keys
        self._values = values

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, item: int) -> object:
        if isinstance(item, int):
            return self._values[item]
        raise KeyError(item)

    def keys(self) -> list[str]:
        return self._keys


@pytest.mark.asyncio
async def test_select_related_nested_long_fk_aliases(db):
    author = await LongJoinAuthor.create()
    book = await LongJoinBook.create(author_model_relation_with_long_name=author)
    chapter = await LongJoinChapter.create(book_model_relation_with_long_name=book)

    queryset = LongJoinChapter.all().select_related(
        "book_model_relation_with_long_name",
        "book_model_relation_with_long_name__author_model_relation_with_long_name",
    )
    sql = queryset.sql()
    author_alias = (
        "longjoinchapter__book_model_relation_with_long_name__"
        "author_model_relation_with_long_name.id"
    )
    assert author_alias in sql
    assert len(author_alias) > 63

    loaded = await queryset.get(id=chapter.id)
    assert loaded.book_model_relation_with_long_name.id == book.id
    assert (
        loaded.book_model_relation_with_long_name.author_model_relation_with_long_name.id
        == author.id
    )


@pytest.mark.asyncio
async def test_select_related_long_o2o_model_and_column(db):
    parent = await LongJoinParent.create(name="parent", this_is_some_long_column_name="long-value")
    child = await ThisIsAnExcessivelyLongOneToOneChildModelName.create(parent=parent)

    queryset = ThisIsAnExcessivelyLongOneToOneChildModelName.filter(id=child.id).select_related(
        "parent"
    )
    sql = queryset.sql()
    long_alias = (
        "thisisanexcessivelylongonetoonechildmodelname__parent.this_is_some_long_column_name"
    )
    assert long_alias in sql
    assert len(long_alias) > 63

    loaded = await queryset.first()
    assert loaded is not None
    assert loaded.parent.id == parent.id
    assert loaded.parent.this_is_some_long_column_name == "long-value"
    assert loaded.parent.name == "parent"


@pytest.mark.asyncio
async def test_select_related_long_aliases_with_only(db):
    parent = await LongJoinParent.create(
        name="only-parent", this_is_some_long_column_name="only-value"
    )
    child = await ThisIsAnExcessivelyLongOneToOneChildModelName.create(parent=parent)

    loaded = await (
        ThisIsAnExcessivelyLongOneToOneChildModelName.filter(id=child.id)
        .only("id", "parent__this_is_some_long_column_name", "parent__name")
        .select_related("parent")
        .first()
    )
    assert loaded is not None
    assert loaded.parent.this_is_some_long_column_name == "only-value"
    assert loaded.parent.name == "only-parent"


def test_row_keys_and_values_prefers_positional_access():
    keys = ["truncated_alias", "truncated_alias"]
    values = ["first", "second"]
    row = _IndexRecord(keys, values)

    got_keys, got_values = BaseExecutor._row_keys_and_values(row)
    assert got_values == values
    assert got_keys == keys
    # dict() would collapse the duplicate truncated keys
    assert list(dict(zip(got_keys, got_values)).values()) != values
