import enum

from pypika.terms import BasicCriterion, Term


class SQLiteRegexMatching(enum.Enum):
    POSIX_REGEX = " REGEXP "


def posix_sqlite_regexp(field: Term, value: str):
    return BasicCriterion(SQLiteRegexMatching.POSIX_REGEX, field, field.wrap_constant(value))


def insensitive_posix_sqlite_regexp(field: Term, value: str):
    return BasicCriterion(
        SQLiteRegexMatching.POSIX_REGEX, field, field.wrap_constant(f"(?i) {value}")
    )
