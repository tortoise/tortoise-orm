from __future__ import annotations

from typing import Any

import pytest
from pypika_tortoise.terms import Field

from tests.testmodels import ModelWithIndexes
from tortoise import fields
from tortoise.exceptions import ConfigurationError
from tortoise.indexes import Index


class CustomIndex(Index):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._foo = ""


# ============================================================================
# Tests for Index hash, equality, and repr (no database needed)
# ============================================================================


def test_index_eq():
    assert Index(fields=("id",)) == Index(fields=("id",))
    assert CustomIndex(fields=("id",)) == CustomIndex(fields=("id",))
    assert Index(fields=("id", "name")) == Index(fields=["id", "name"])

    assert Index(fields=("id", "name")) != Index(fields=("name", "id"))
    assert Index(fields=("id",)) != Index(fields=("name",))
    assert CustomIndex(fields=("id",)) != Index(fields=("id",))


def test_index_hash():
    assert hash(Index(fields=("id",))) == hash(Index(fields=("id",)))
    assert hash(Index(fields=("id", "name"))) == hash(Index(fields=["id", "name"]))
    assert hash(CustomIndex(fields=("id", "name"))) == hash(CustomIndex(fields=["id", "name"]))

    assert hash(Index(fields=("id", "name"))) != hash(Index(fields=["name", "id"]))
    assert hash(Index(fields=("id",))) != hash(Index(fields=("name",)))

    indexes = {Index(fields=("id",))}
    indexes.add(Index(fields=("id",)))
    assert len(indexes) == 1
    indexes.add(CustomIndex(fields=("id",)))
    assert len(indexes) == 2
    indexes.add(Index(fields=("name",)))
    assert len(indexes) == 3


def test_index_repr():
    assert repr(Index(fields=("id",))) == "Index(fields=['id'])"
    assert repr(Index(fields=("id", "name"))) == "Index(fields=['id', 'name'])"
    assert repr(Index(fields=("id",), name="MyIndex")) == "Index(fields=['id'], name='MyIndex')"
    assert repr(Index(Field("id"))) == f"Index({str(Field('id'))})"
    assert repr(Index(Field("a"), name="Id")) == f"Index({str(Field('a'))}, name='Id')"
    with pytest.raises(ConfigurationError):
        Index(Field("id"), fields=("name",))


# ============================================================================
# Tests for index/db_index field alias (no database needed)
# ============================================================================


def _test_index_alias_for_field(field_class: Any, init_kwargs: dict | None = None):
    """Helper function to test index alias behavior for a given field class."""
    kwargs: dict = init_kwargs or {}

    with pytest.warns(
        DeprecationWarning, match="`index` is deprecated, please use `db_index` instead"
    ):
        f = field_class(index=True, **kwargs)
    assert f.index is True

    with pytest.warns(
        DeprecationWarning, match="`index` is deprecated, please use `db_index` instead"
    ):
        f = field_class(index=False, **kwargs)
    assert f.index is False

    f = field_class(db_index=True, **kwargs)
    assert f.index is True

    f = field_class(db_index=True, index=True, **kwargs)
    assert f.index is True

    f = field_class(db_index=False, **kwargs)
    assert f.index is False

    f = field_class(db_index=False, index=False, **kwargs)
    assert f.index is False

    with pytest.raises(ConfigurationError, match="can't set both db_index and index"):
        field_class(db_index=False, index=True, **kwargs)

    with pytest.raises(ConfigurationError, match="can't set both db_index and index"):
        field_class(db_index=True, index=False, **kwargs)


def test_index_alias_int_field():
    _test_index_alias_for_field(fields.IntField)


def test_index_alias_small_int_field():
    _test_index_alias_for_field(fields.SmallIntField)


def test_index_alias_big_int_field():
    _test_index_alias_for_field(fields.BigIntField)


def test_index_alias_uuid_field():
    _test_index_alias_for_field(fields.UUIDField)


def test_index_alias_char_field():
    _test_index_alias_for_field(fields.CharField, init_kwargs={"max_length": 10})


# ============================================================================
# Tests for ModelWithIndexes metadata (requires database fixture)
# ============================================================================


@pytest.mark.asyncio
async def test_model_with_indexes_meta(db):
    assert ModelWithIndexes._meta.indexes == [
        Index(fields=("f1", "f2")),
        Index(fields=("f3",), name="model_with_indexes__f3"),
    ]
    assert ModelWithIndexes._meta.fields_map["id"].index
    assert ModelWithIndexes._meta.fields_map["indexed"].index
    assert ModelWithIndexes._meta.fields_map["unique_indexed"].unique
