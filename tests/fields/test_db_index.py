from typing import Any

from tortoise import fields
from tortoise.contrib import test
from tortoise.exceptions import ConfigurationError


class TestIndexAlias(test.TestCase):
    Field: Any = fields.IntField

    def test_index_alias(self) -> None:
        kwargs: dict = getattr(self, "init_kwargs", {})
        with self.assertWarnsRegex(
            DeprecationWarning, "`index` is deprecated, please use `db_index` instead"
        ):
            f = self.Field(index=True, **kwargs)
        assert f.index is True
        with self.assertWarnsRegex(
            DeprecationWarning, "`index` is deprecated, please use `db_index` instead"
        ):
            f = self.Field(index=False, **kwargs)
        assert f.index is False
        f = self.Field(db_index=True, **kwargs)
        assert f.index is True
        f = self.Field(db_index=True, index=True, **kwargs)
        assert f.index is True
        f = self.Field(db_index=False, **kwargs)
        assert f.index is False
        f = self.Field(db_index=False, index=False, **kwargs)
        assert f.index is False
        with self.assertRaisesRegex(ConfigurationError, "can't set both db_index and index"):
            self.Field(db_index=False, index=True, **kwargs)
        with self.assertRaisesRegex(ConfigurationError, "can't set both db_index and index"):
            self.Field(db_index=True, index=False, **kwargs)


class TestIndexAliasSmallInt(TestIndexAlias):
    Field = fields.SmallIntField


class TestIndexAliasBigInt(TestIndexAlias):
    Field = fields.BigIntField


class TestIndexAliasUUID(TestIndexAlias):
    Field = fields.UUIDField


class TestIndexAliasChar(TestIndexAlias):
    Field = fields.CharField
    init_kwargs = {"max_length": 10}
