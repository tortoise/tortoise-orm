import json
import operator
from typing import Any, Callable, Dict, List

from pypika.enums import JSONOperators
from pypika.terms import BasicCriterion, Criterion, Term, ValueWrapper

from tortoise.filters import is_null, not_equal, not_null


def postgres_json_contains(field: Term, value: str) -> Criterion:
    return BasicCriterion(JSONOperators.CONTAINS, field, ValueWrapper(value))


def postgres_json_contained_by(field: Term, value: str) -> Criterion:
    return BasicCriterion(JSONOperators.CONTAINED_BY, field, ValueWrapper(value))


operator_keywords = {
    "not": not_equal,
    "isnull": is_null,
    "not_isnull": not_null,
}


def _get_json_criterion(items: List):
    if len(items) == 2:
        left = items.pop(0)
        right = items.pop(0)
        return BasicCriterion(JSONOperators.GET_TEXT_VALUE, ValueWrapper(left), ValueWrapper(right))

    left = items.pop(0)
    return BasicCriterion(
        JSONOperators.GET_JSON_VALUE, ValueWrapper(left), _get_json_criterion(items)
    )


def _create_json_criterion(items: List, field_term: Term, operator_: Callable, value: str):
    if len(items) == 1:
        term = items.pop(0)
        return operator_(
            BasicCriterion(JSONOperators.GET_TEXT_VALUE, field_term, ValueWrapper(term)), value
        )

    return operator_(
        BasicCriterion(JSONOperators.GET_JSON_VALUE, field_term, _get_json_criterion(items)), value
    )


def _serialize_value(value: Any):
    if type(value) in [dict, list]:
        return json.dumps(value)
    return value


def postgres_json_filter(field: Term, value: Dict) -> Criterion:
    ((key, filter_value),) = value.items()
    filter_value = _serialize_value(filter_value)
    key_parts = [int(item) if item.isdigit() else str(item) for item in key.split("__")]
    operator_ = operator.eq
    if key_parts[-1] in operator_keywords:
        operator_ = operator_keywords[str(key_parts.pop(-1))]

    return _create_json_criterion(key_parts, field, operator_, filter_value)
