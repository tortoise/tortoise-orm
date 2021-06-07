import json
import operator
from typing import Any, Dict, List

from pypika.functions import Cast
from pypika.terms import Criterion
from pypika.terms import Function as PypikaFunction
from pypika.terms import Term, ValueWrapper

from tortoise.filters import not_equal


class JSONContains(PypikaFunction):  # type: ignore
    def __init__(self, column_name: Term, target_list: Term):
        super(JSONContains, self).__init__("JSON_CONTAINS", column_name, target_list)


class JSONExtract(PypikaFunction):  # type: ignore
    def __init__(self, column_name: Term, query_list: List[Term]):
        query = self.make_query(query_list)
        super(JSONExtract, self).__init__("JSON_EXTRACT", column_name, query)

    @classmethod
    def serialize_value(cls, value: Any):
        if isinstance(value, int):
            return f"[{value}]"
        if isinstance(value, str):
            return f".{value}"

    def make_query(self, query_list: List[Term]):
        query = ["$"]
        for value in query_list:
            query.append(self.serialize_value(value))

        return "".join(query)


def mysql_json_contains(field: Term, value: str) -> Criterion:
    return JSONContains(field, ValueWrapper(value))


def mysql_json_contained_by(field: Term, value_str: str) -> Criterion:
    values = json.loads(value_str)
    contained_by = None
    for value in values:
        if contained_by is None:
            contained_by = JSONContains(field, ValueWrapper(json.dumps([value])))
        else:
            contained_by |= JSONContains(field, ValueWrapper(json.dumps([value])))  # type: ignore
    return contained_by


def _mysql_json_is_null(left: Term, is_null: bool):
    if is_null is True:
        return operator.eq(left, Cast("null", "JSON"))
    else:
        return not_equal(left, Cast("null", "JSON"))


def _mysql_json_not_is_null(left: Term, is_null: bool):
    return _mysql_json_is_null(left, not is_null)


operator_keywords = {
    "not": not_equal,
    "isnull": _mysql_json_is_null,
    "not_isnull": _mysql_json_not_is_null,
}


def _serialize_value(value: Any):
    if type(value) in [dict, list]:
        return json.dumps(value)
    return value


def mysql_json_filter(field: Term, value: Dict) -> Criterion:
    ((key, filter_value),) = value.items()
    filter_value = _serialize_value(filter_value)
    key_parts = list(map(lambda item: int(item) if item.isdigit() else str(item), key.split("__")))
    operator_ = operator.eq
    if key_parts[-1] in operator_keywords:
        operator_ = operator_keywords[str(key_parts.pop(-1))]

    return operator_(JSONExtract(field, key_parts), filter_value)
