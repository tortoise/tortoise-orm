import enum
from typing import cast

from pypika_tortoise.terms import BasicCriterion, Term


class PostgresRegexMatching(enum.Enum):
    posix_regex = "~"


def postgres_posix_regex(field: Term, value: str) -> BasicCriterion:
    term = cast(Term, field.wrap_constant(value))
    return BasicCriterion(PostgresRegexMatching.posix_regex, field, term)
