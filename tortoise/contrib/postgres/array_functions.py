from enum import Enum
from typing import Any, Sequence, Union

from pypika_tortoise.terms import Array, BasicCriterion, Criterion, Term
from pypika_tortoise.functions import Function


class PostgresArrayOperators(str, Enum):
    CONTAINS = "@>"
    CONTAINED_BY = "<@"
    OVERLAP = "&&"


def postgres_array_contains(field: Term, value: Union[Any, Sequence[Any]]) -> Criterion:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        value = (value,)

    return BasicCriterion(PostgresArrayOperators.CONTAINS, field, Array(*value))


def postgres_array_contained_by(field: Term, value: Sequence[Any]) -> Criterion:
    return BasicCriterion(PostgresArrayOperators.CONTAINED_BY, field, Array(*value))


def postgres_array_overlap(field: Term, value: Sequence[Any]) -> Criterion:
    return BasicCriterion(PostgresArrayOperators.OVERLAP, field, Array(*value))


def postgres_array_length(field: Term, value: int) -> Criterion:
    """Returns a criterion that checks if array length equals the given value"""
    return Function("array_length", field, 1).eq(value)
