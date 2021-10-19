from typing import TYPE_CHECKING, Optional, Set, Type

from pypika.terms import Term

if TYPE_CHECKING:
    from tortoise import Model
    from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class Index:
    INDEX_TYPE = ""
    INDEX_CREATE_TEMPLATE = (
        "CREATE{index_type}INDEX {exists}{index_name} ON {table_name} ({fields}){extra};"
    )

    def __init__(
        self,
        *expressions: Term,
        fields: Optional[Set[str]] = None,
        name: Optional[str] = None,
    ):
        """
        All kinds of index parent class, default is BTreeIndex.

        :param expressions: The expressions of on which the index is desired.
        :param fields: A list or tuple of the name of the fields on which the index is desired.
        :param name: The name of the index.
        :raises ValueError: If params conflict.
        """
        self.fields = list(fields or [])
        if not expressions and not fields:
            raise ValueError("At least one field or expression is required to define an " "index.")
        if expressions and fields:
            raise ValueError(
                "Index.fields and expressions are mutually exclusive.",
            )
        self.name = name
        self.expressions = expressions
        self.extra = ""

    def get_sql(self, schema_generator: "BaseSchemaGenerator", model: "Type[Model]", safe: bool):
        if self.fields:
            return self.INDEX_CREATE_TEMPLATE.format(
                exists="IF NOT EXISTS " if safe else "",
                index_name=schema_generator.quote(
                    self.name or schema_generator._generate_index_name("idx", model, self.fields)
                ),
                index_type=f" {self.INDEX_TYPE} ",
                table_name=schema_generator.quote(model._meta.db_table),
                fields=", ".join(schema_generator.quote(f) for f in self.fields),
                extra=self.extra,
            )

        expressions = [f"({expression.get_sql()})" for expression in self.expressions]
        return self.INDEX_CREATE_TEMPLATE.format(
            exists="IF NOT EXISTS " if safe else "",
            index_name=schema_generator.quote(
                self.name or schema_generator._generate_index_name("idx", model, expressions)
            ),
            index_type=f" {self.INDEX_TYPE} ",
            table_name=schema_generator.quote(model._meta.db_table),
            fields=", ".join(expressions),
            extra=self.extra,
        )
