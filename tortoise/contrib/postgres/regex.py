import enum

from pypika.terms import BasicCriterion, Term


class PostgresRegexMatching(enum.Enum):
    POSIX_REGEX = " ~ "
    IPOSIX_REGEX = " *~ "


def postgres_posix_regex(field: Term, value: str):
    return BasicCriterion(PostgresRegexMatching.POSIX_REGEX, field, field.wrap_constant(value))


def postgres_insensitive_posix_regex(field: Term, value: str):
    return BasicCriterion(PostgresRegexMatching.IPOSIX_REGEX, field, field.wrap_constant(value))
