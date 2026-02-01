from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pypika_tortoise.context import DEFAULT_SQL_CONTEXT
from pypika_tortoise.terms import Term, ValueWrapper

from tortoise.exceptions import ConfigurationError
from tortoise.expressions import Expression, ResolveContext

if TYPE_CHECKING:
    from tortoise.backends.base.schema_generator import BaseSchemaGenerator
    from tortoise.models import Model


class Index:
    INDEX_TYPE = ""

    def __init__(
        self,
        *expressions: Term | Expression,
        fields: tuple[str, ...] | list[str] | None = None,
        name: str | None = None,
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
            raise ConfigurationError(
                "At least one field or expression is required to define an index."
            )
        if expressions and fields:
            raise ConfigurationError(
                "Index.fields and expressions are mutually exclusive.",
            )
        self.name = name
        self.expressions = expressions
        self._expressions_resolved = False
        self.extra = ""

    def describe(self) -> dict:
        return {
            "fields": self.fields,
            "expressions": [str(expression) for expression in self.expressions],
            "name": self.name,
            "type": self.INDEX_TYPE,
            "extra": self.extra,
        }

    def deconstruct(self) -> tuple[str, list[Any], dict[str, Any]]:
        path = f"{self.__class__.__module__}.{self.__class__.__name__}"
        args = list(self.expressions)
        kwargs: dict[str, Any] = {}
        if self.fields:
            kwargs["fields"] = list(self.fields)
        if self.name:
            kwargs["name"] = self.name
        return path, args, kwargs

    def index_name(self, schema_generator: BaseSchemaGenerator, model: type[Model]) -> str:
        # This function is required by aerich
        self.resolve_expressions(model)
        return self.name or schema_generator._get_index_name("idx", model, self.field_names)

    def get_sql(self, schema_generator: BaseSchemaGenerator, model: type[Model], safe: bool) -> str:
        self.resolve_expressions(model)
        # This function is required by aerich
        return schema_generator._get_index_sql(
            model,
            self.field_names,
            safe,
            index_name=self.name,
            index_type=self.INDEX_TYPE,
            extra=self.extra,
        )

    def resolve_expressions(self, model: type[Model]) -> None:
        if self._expressions_resolved or not self.expressions:
            return
        if not any(isinstance(expression, Expression) for expression in self.expressions):
            self._expressions_resolved = True
            return
        resolve_context = ResolveContext(
            model=model,
            table=model.get_table(),
            annotations={},
            custom_filters=model._meta.filters,
        )
        resolved: list[Term] = []
        for expression in self.expressions:
            if isinstance(expression, Expression):
                result = expression.resolve(resolve_context)
                resolved.append(result.term)
            else:
                resolved.append(expression)
        self.expressions = tuple(resolved)
        self._expressions_resolved = True

    @property
    def field_names(self) -> list[str]:
        if self.fields:
            return list(self.fields)
        elif self.expressions:
            if any(isinstance(expression, Expression) for expression in self.expressions):
                raise ConfigurationError(
                    "Index expressions must be resolved before accessing field_names."
                )
            return [
                f"({cast(Term, expression).get_sql(DEFAULT_SQL_CONTEXT)})"
                for expression in self.expressions
            ]
        else:
            raise ConfigurationError(
                "At least one field or expression is required to define an index."
            )

    def __repr__(self) -> str:
        argument = ""
        if self.expressions:
            argument += ", ".join(map(str, self.expressions))
        if fields := self.fields:
            argument += f"{fields=}"
        if name := self.name:
            argument += f", {name=}"
        return self.__class__.__name__ + "(" + argument + ")"

    def __hash__(self) -> int:
        return hash((tuple(self.fields), self.name, tuple(self.expressions)))

    def __eq__(self, other: Any) -> bool:
        return type(self) is type(other) and self.__dict__ == other.__dict__


class PartialIndex(Index):
    def __init__(
        self,
        *expressions: Term | Expression,
        fields: tuple[str, ...] | list[str] | None = None,
        name: str | None = None,
        condition: dict | None = None,
    ) -> None:
        super().__init__(*expressions, fields=fields, name=name)
        self.condition = condition
        if condition:
            cond = " WHERE "
            items = [f"{k} = {ValueWrapper(v)}" for k, v in condition.items()]
            cond += " AND ".join(items)
            self.extra = cond

    def deconstruct(self) -> tuple[str, list[Any], dict[str, Any]]:
        path, args, kwargs = super().deconstruct()
        if self.condition:
            kwargs["condition"] = self.condition
        return path, args, kwargs
