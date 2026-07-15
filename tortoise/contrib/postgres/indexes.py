from __future__ import annotations

from typing import Any

from pypika_tortoise.terms import Term

from tortoise.expressions import Expression
from tortoise.indexes import PartialIndex


class PostgreSQLIndex(PartialIndex):
    """
    Base class for PostgreSQL-specific indexes.

    :param expressions: The expressions on which the index is desired.
    :param fields: A tuple or list of field names on which the index is desired.
    :param name: The name of the index.
    :param condition: Optional WHERE condition for partial indexes.
    :param unique: Whether the index should enforce uniqueness.
    :param nulls_not_distinct: For unique indexes, treat NULL values as equal.
    :raises ValueError: If params conflict.
    """

    def __init__(
        self,
        *expressions: Term | Expression,
        fields: tuple[str, ...] | list[str] | None = None,
        name: str | None = None,
        condition: dict | None = None,
        unique: bool = False,
        nulls_not_distinct: bool = False,
    ) -> None:
        super().__init__(*expressions, fields=fields, name=name, condition=condition)
        self.unique = unique
        self.nulls_not_distinct = nulls_not_distinct

    def get_sql(self, schema_generator, model, safe):
        return schema_generator._get_index_sql(
            model,
            self.field_names,
            safe,
            index_name=self.name,
            index_type=self.INDEX_TYPE,
            extra=self.extra,
            unique=self.unique,
            nulls_not_distinct=self.nulls_not_distinct,
        )

    def describe(self) -> dict:
        result = super().describe()
        result["unique"] = self.unique
        result["nulls_not_distinct"] = self.nulls_not_distinct
        return result

    def deconstruct(self) -> tuple[str, list[Any], dict[str, Any]]:
        path, args, kwargs = super().deconstruct()
        if self.unique:
            kwargs["unique"] = self.unique
        if self.nulls_not_distinct:
            kwargs["nulls_not_distinct"] = self.nulls_not_distinct
        return path, args, kwargs


class BloomIndex(PostgreSQLIndex):
    INDEX_TYPE = "BLOOM"


class BrinIndex(PostgreSQLIndex):
    INDEX_TYPE = "BRIN"


class GinIndex(PostgreSQLIndex):
    INDEX_TYPE = "GIN"


class GistIndex(PostgreSQLIndex):
    INDEX_TYPE = "GIST"


class HashIndex(PostgreSQLIndex):
    INDEX_TYPE = "HASH"


class SpGistIndex(PostgreSQLIndex):
    INDEX_TYPE = "SPGIST"
