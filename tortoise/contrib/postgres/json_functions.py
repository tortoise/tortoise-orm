from __future__ import annotations

import operator
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Tuple, cast

from pypika.enums import JSONOperators
from pypika.functions import Cast
from pypika.terms import BasicCriterion, Criterion, Term, ValueWrapper

from tortoise.filters import (
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
    get_json_filter_operator,
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


operator_keywords: dict[str, Callable[..., Criterion]] = {
    "not": not_equal,
    "isnull": is_null,
    "not_isnull": not_null,
    "in": is_in,
    "not_in": not_in,
    "gte": cast(Callable[..., Criterion], operator.ge),
    "gt": cast(Callable[..., Criterion], operator.gt),
    "lte": cast(Callable[..., Criterion], operator.le),
    "lt": cast(Callable[..., Criterion], operator.lt),
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


def _get_json_path(key_parts: list[str | int]) -> Criterion:
    """
    Recursively build a JSON path from a list of key parts, e.g. ['a', 'b', 'c'] -> 'a'->'b'->>'c'
    """
    if len(key_parts) == 2:
        left = key_parts.pop(0)
        right = key_parts.pop(0)
        return BasicCriterion(
            JSONOperators.GET_TEXT_VALUE, _wrap_key_part(left), _wrap_key_part(right)
        )

    left = key_parts.pop(0)
    return BasicCriterion(
        JSONOperators.GET_JSON_VALUE, ValueWrapper(left), _get_json_path(key_parts)
    )


def _wrap_key_part(key_part: str | int) -> Term:
    if isinstance(key_part, int):
        # Letting Postgres know that the parameter is an integer, otherwise,
        # it will fail with a type error.
        return Cast(ValueWrapper(key_part), "int")
    return ValueWrapper(key_part)


def _create_json_criterion(
    key_parts: list[str | int], field_term: Term, operator_: Callable, value: Any
):
    criteria: Tuple[Criterion, str]
    if len(key_parts) == 1:
        criteria = (
            BasicCriterion(
                JSONOperators.GET_TEXT_VALUE,
                field_term,
                _wrap_key_part(key_parts.pop(0)),
            ),
            value,
        )
    else:
        criteria = (
            BasicCriterion(JSONOperators.GET_JSON_VALUE, field_term, _get_json_path(key_parts)),
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
    ] or isinstance(value, (date, datetime)):
        criteria = Cast(criteria[0], "timestamp"), criteria[1]
    elif operator_ in [
        operator.gt,
        operator.ge,
        operator.lt,
        operator.le,
        between_and,
    ] or type(
        value
    ) in (int, float, Decimal):
        criteria = Cast(criteria[0], "numeric"), criteria[1]

    return operator_(*criteria)


def postgres_json_filter(field: Term, value: dict) -> Criterion:
    key_parts, filter_value, operator_ = get_json_filter_operator(value, operator_keywords)
    return _create_json_criterion(key_parts, field, operator_, filter_value)
