import enum

from pypika.terms import BasicCriterion, Term


class PostgresRegexMatching(enum.Enum):
    posix_regex = "~"


def postgres_posix_regex(field: Term, value: str):
    return BasicCriterion(PostgresRegexMatching.posix_regex, field, field.wrap_constant(value))
