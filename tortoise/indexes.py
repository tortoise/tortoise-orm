from typing import TYPE_CHECKING, Optional, Tuple, Type

from pypika.terms import Term, ValueWrapper

if TYPE_CHECKING:
    from tortoise import Model
    from tortoise.backends.base.schema_generator import BaseSchemaGenerator


class Index:
    INDEX_TYPE = ""
    INDEX_CREATE_TEMPLATE = (
        "CREATE{index_type}INDEX {index_name} ON {table_name} ({fields}){extra};"
    )

    def __init__(
        self,
        *expressions: Term,
        fields: Optional[Tuple[str, ...]] = None,
        name: Optional[str] = None,
    ) -> None:
        """
        All kinds of index parent class, default is BTreeIndex.

        :param expressions: The expressions of on which the index is desired.
        :param fields: A tuple of names of the fields on which the index is desired.
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

    def get_sql(
        self, schema_generator: "BaseSchemaGenerator", model: "Type[Model]", safe: bool
    ) -> str:
        if self.fields:
            fields = ", ".join(schema_generator.quote(f) for f in self.fields)
        else:
            expressions = [f"({expression.get_sql()})" for expression in self.expressions]
            fields = ", ".join(expressions)

        return self.INDEX_CREATE_TEMPLATE.format(
            exists="IF NOT EXISTS " if safe else "",
            index_name=schema_generator.quote(self.index_name(schema_generator, model)),
            index_type=f" {self.INDEX_TYPE} ",
            table_name=schema_generator.quote(model._meta.db_table),
            fields=fields,
            extra=self.extra,
        )

    def index_name(self, schema_generator: "BaseSchemaGenerator", model: "Type[Model]") -> str:
        return self.name or schema_generator._generate_index_name("idx", model, self.fields)


class PartialIndex(Index):
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
            items = [f"{k} = {ValueWrapper(v)}" for k, v in condition.items()]
            cond += " AND ".join(items)
            self.extra = cond
