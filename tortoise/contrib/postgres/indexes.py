from typing import Optional, Tuple, Type

from pypika.terms import Term, ValueWrapper

from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.indexes import PartialIndex
from tortoise.models import Model


class PostgreSQLIndex(PartialIndex):
    INDEX_CREATE_TEMPLATE = (
        "CREATE INDEX {exists}{index_name} ON {table_name} USING{index_type}({fields}){extra};"
    )

    def __init__(
        self,
        *expressions: Term,
        fields: Optional[Tuple[str, ...]] = None,
        name: Optional[str] = None,
        condition: Optional[dict] = None,
    ) -> None:
        super().__init__(*expressions, fields=fields, name=name)
        if condition:
            cond = " WHERE "
            items = []
            for k, v in condition.items():
                items.append(f"{k} = {ValueWrapper(v)}")
            cond += " AND ".join(items)
            self.extra = cond


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


class PostgresUniqueIndex(PostgreSQLIndex):
    INDEX_CREATE_TEMPLATE = PostgreSQLIndex.INDEX_CREATE_TEMPLATE.replace(
        "CREATE", "CREATE UNIQUE"
    ).replace("USING", "")

    def __init__(
        self,
        *expressions: Term,
        fields: Optional[Tuple[str]] = None,
        name: Optional[str] = None,
        condition: Optional[dict] = None,
        nulls_not_distinct: bool = False,
    ):
        super().__init__(*expressions, fields=fields, name=name, condition=condition)
        if nulls_not_distinct:
            self.extra = " nulls not distinct".upper() + self.extra

    def get_sql(self, schema_generator: BaseSchemaGenerator, model: Type[Model], safe: bool):
        if self.INDEX_TYPE:
            self.INDEX_TYPE = f"USING {self.INDEX_TYPE}"
        return super().get_sql(schema_generator, model, safe)
