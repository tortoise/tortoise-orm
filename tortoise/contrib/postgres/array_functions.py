from enum import Enum

from pypika_tortoise.terms import BasicCriterion, Criterion, Function, Term


class PostgresArrayOperators(str, Enum):
    CONTAINS = "@>"
    CONTAINED_BY = "<@"
    OVERLAP = "&&"


# The value in the functions below is casted to the exact type of the field with value_encoder
# to avoid issues with psycopg that tries to use the smallest possible type which can lead to errors,
# e.g. {1,2} will be casted to smallint[] instead of integer[].


def postgres_array_contains(field: Term, value: Term) -> Criterion:
    return BasicCriterion(PostgresArrayOperators.CONTAINS, field, value)


def postgres_array_contained_by(field: Term, value: Term) -> Criterion:
    return BasicCriterion(PostgresArrayOperators.CONTAINED_BY, field, value)


def postgres_array_overlap(field: Term, value: Term) -> Criterion:
    return BasicCriterion(PostgresArrayOperators.OVERLAP, field, value)


def postgres_array_length(field: Term, value: int) -> Criterion:
    """Returns a criterion that checks if array length equals the given value"""
    return Function("array_length", field, 1).eq(value)
