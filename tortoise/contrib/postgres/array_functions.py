from enum import Enum
from typing import Any, Sequence, Union

from pypika_tortoise.terms import Array, BasicCriterion, Criterion, Term


class PostgresArrayOperators(str, Enum):
    CONTAINS = "@>"


def postgres_array_contains(field: Term, value: Union[Any, Sequence[Any]]) -> Criterion:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        value = (value,)

    return BasicCriterion(PostgresArrayOperators.CONTAINS, field, Array(*value))
