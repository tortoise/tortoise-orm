from __future__ import annotations

from typing import Any

from pypika_tortoise.terms import Term, ValueWrapper

from tortoise.exceptions import ConfigurationError


class Index:
    INDEX_TYPE = ""

    def __init__(
        self,
        *expressions: Term,
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
                "At least one field or expression is required to define an " "index."
            )
        if expressions and fields:
            raise ConfigurationError(
                "Index.fields and expressions are mutually exclusive.",
            )
        self.name = name
        self.expressions = expressions
        self.extra = ""

    def describe(self) -> dict:
        return {
            "fields": self.fields,
            "expressions": [str(expression) for expression in self.expressions],
            "name": self.name,
            "type": self.INDEX_TYPE,
            "extra": self.extra,
        }

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
        *expressions: Term,
        fields: tuple[str, ...] | list[str] | None = None,
        name: str | None = None,
        condition: dict | None = None,
    ) -> None:
        super().__init__(*expressions, fields=fields, name=name)
        if condition:
            cond = " WHERE "
            items = [f"{k} = {ValueWrapper(v)}" for k, v in condition.items()]
            cond += " AND ".join(items)
            self.extra = cond
