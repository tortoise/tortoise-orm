from __future__ import annotations

import json
import operator
from typing import Any

from pypika_tortoise.functions import Cast
from pypika_tortoise.terms import Criterion
from pypika_tortoise.terms import Function as PypikaFunction
from pypika_tortoise.terms import Term, ValueWrapper

from tortoise.filters import get_json_filter_operator, not_equal


class JSONContains(PypikaFunction):
    def __init__(self, column_name: Term, target_list: Term) -> None:
        super().__init__("JSON_CONTAINS", column_name, target_list)


class JSONExtract(PypikaFunction):
    def __init__(self, column_name: Term, query_list: list[int | str | Term]) -> None:
        query = self.make_query(query_list)
        super().__init__("JSON_EXTRACT", column_name, query)

    @classmethod
    def serialize_value(cls, value: Any) -> str:
        if isinstance(value, int):
            return f"[{value}]"
        if isinstance(value, str):
            return f".{value}"
        return str(value)

    def make_query(self, query_list: list[Term | int | str]) -> str:
        query = ["$"]
        for value in query_list:
            query.append(self.serialize_value(value))

        return "".join(query)


def mysql_json_contains(field: Term, value: str) -> Criterion:
    return JSONContains(field, ValueWrapper(value))


def mysql_json_contained_by(field: Term, value_str: str) -> JSONContains | None:
    values = json.loads(value_str)
    contained_by = None
    for value in values:
        if contained_by is None:
            contained_by = JSONContains(field, ValueWrapper(json.dumps([value])))
        else:
            contained_by |= JSONContains(field, ValueWrapper(json.dumps([value])))  # type: ignore
    return contained_by


def _mysql_json_is_null(left: Term, is_null: bool) -> Criterion:
    if is_null:
        return operator.eq(left, Cast("null", "JSON"))
    else:
        return not_equal(left, Cast("null", "JSON"))


def _mysql_json_not_is_null(left: Term, is_null: bool) -> Criterion:
    return _mysql_json_is_null(left, not is_null)


operator_keywords = {
    "not": not_equal,
    "isnull": _mysql_json_is_null,
    "not_isnull": _mysql_json_not_is_null,
}


def mysql_json_filter(field: Term, value: dict) -> Criterion:
    key_parts, filter_value, operator_ = get_json_filter_operator(value, operator_keywords)
    return operator_(JSONExtract(field, key_parts), filter_value)  # type:ignore[arg-type]
