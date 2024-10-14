import enum
from typing import cast

from pypika.terms import BasicCriterion, Term


class PostgresRegexMatching(enum.Enum):
    POSIX_REGEX = " ~ "
    IPOSIX_REGEX = " *~ "


def postgres_posix_regex(field: Term, value: str):
    term = cast(Term, field.wrap_constant(value))
    return BasicCriterion(PostgresRegexMatching.POSIX_REGEX, field, term)


def postgres_insensitive_posix_regex(field: Term, value: str):
    term = cast(Term, field.wrap_constant(value))
    return BasicCriterion(PostgresRegexMatching.IPOSIX_REGEX, field, term)
