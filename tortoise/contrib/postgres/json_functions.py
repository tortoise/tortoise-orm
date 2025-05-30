from __future__ import annotations

import operator
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from pypika_tortoise.enums import JSONOperators
from pypika_tortoise.functions import Cast
from pypika_tortoise.terms import BasicCriterion, Criterion, Term, ValueWrapper

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
from tortoise.query_utils import get_json_filter_operator, resolve_field_json_path


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


def _create_json_criterion(
    key_parts: list[str | int], field_term: Term, operator_: Callable, value: Any
):
    criteria: tuple[Term, str] = resolve_field_json_path(field_term, key_parts), value

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
