from __future__ import annotations

import operator
from typing import Callable

from pypika.enums import JSONOperators
from pypika.functions import Cast
from pypika.terms import BasicCriterion, Criterion, Term, ValueWrapper

from tortoise.filters import (
    get_json_filter_operator,
    between_and,
    contains,
    ends_with,
    extract_day_equal,
    extract_hour_equal,
    extract_microsecond_equal,
    extract_minute_equal,
    extract_month_equal,
    extract_quarter_equal,
    extract_second_equal,
    extract_week_equal,
    extract_year_equal,
    insensitive_contains,
    insensitive_ends_with,
    insensitive_exact,
    insensitive_starts_with,
    is_in,
    is_null,
    not_equal,
    not_in,
    not_null,
    starts_with,
)


def postgres_json_contains(field: Term, value: str) -> Criterion:
    return BasicCriterion(JSONOperators.CONTAINS, field, ValueWrapper(value))


def postgres_json_contained_by(field: Term, value: str) -> Criterion:
    return BasicCriterion(JSONOperators.CONTAINED_BY, field, ValueWrapper(value))


operator_keywords = {
    "not": not_equal,
    "isnull": is_null,
    "not_isnull": not_null,
    "in": is_in,
    "not_in": not_in,
    "gte": operator.ge,
    "gt": operator.gt,
    "lte": operator.le,
    "lt": operator.lt,
    "range": between_and,
    "contains": contains,
    "startswith": starts_with,
    "endswith": ends_with,
    "iexact": insensitive_exact,
    "icontains": insensitive_contains,
    "istartswith": insensitive_starts_with,
    "iendswith": insensitive_ends_with,
    "year": extract_year_equal,
    "quarter": extract_quarter_equal,
    "month": extract_month_equal,
    "week": extract_week_equal,
    "day": extract_day_equal,
    "hour": extract_hour_equal,
    "minute": extract_minute_equal,
    "second": extract_second_equal,
    "microsecond": extract_microsecond_equal,
}


def _get_json_criterion(items: list):
    if len(items) == 2:
        left = items.pop(0)
        right = items.pop(0)
        return BasicCriterion(JSONOperators.GET_TEXT_VALUE, ValueWrapper(left), ValueWrapper(right))

    left = items.pop(0)
    return BasicCriterion(
        JSONOperators.GET_JSON_VALUE, ValueWrapper(left), _get_json_criterion(items)
    )


def _create_json_criterion(items: list, field_term: Term, operator_: Callable, value: str):
    if len(items) == 1:
        term = items.pop(0)
        criteria = (
            BasicCriterion(JSONOperators.GET_TEXT_VALUE, field_term, ValueWrapper(term, allow_parametrize=False)),
            value,
        )
    else:
        criteria = (
            BasicCriterion(JSONOperators.GET_JSON_VALUE, field_term, _get_json_criterion(items)),
            value,
        )

    if operator_ in [
        extract_day_equal,
        extract_hour_equal,
        extract_microsecond_equal,
        extract_minute_equal,
        extract_month_equal,
        extract_quarter_equal,
        extract_second_equal,
        extract_week_equal,
        extract_year_equal,
    ]:
        criteria = Cast(criteria[0], "timestamp"), criteria[1]

    return operator_(*criteria)


def postgres_json_filter(field: Term, value: dict) -> Criterion:
    key_parts, filter_value, operator_ = get_json_filter_operator(value, operator_keywords)
    return _create_json_criterion(key_parts, field, operator_, filter_value)
