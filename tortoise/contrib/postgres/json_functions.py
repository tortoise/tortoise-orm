from typing import Callable, Dict, List

from pypika.enums import JSONOperators
from pypika.terms import BasicCriterion, Criterion, Term, ValueWrapper

from tortoise.filters import get_json_filter_operator, is_null, not_equal, not_null


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


def postgres_json_filter(field: Term, value: Dict) -> Criterion:
    key_parts, filter_value, operator_ = get_json_filter_operator(value, operator_keywords)
    return _create_json_criterion(key_parts, field, operator_, filter_value)
