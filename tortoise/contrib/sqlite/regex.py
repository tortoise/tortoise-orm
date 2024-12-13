import enum
import re
from typing import cast

import aiosqlite
from pypika.terms import BasicCriterion, Term, Function


class SQLiteRegexMatching(enum.Enum):
    POSIX_REGEX = " REGEXP "
    IPOSIX_REGEX = " MATCH "


def posix_sqlite_regexp(field: Term, value: str):
    term = cast(Term, field.wrap_constant(value))
    return BasicCriterion(SQLiteRegexMatching.POSIX_REGEX, field, term)
    # return Function("regexp", field, term)


def insensitive_posix_sqlite_regexp(field: Term, value: str):
    term = cast(Term, field.wrap_constant(value))
    return BasicCriterion(SQLiteRegexMatching.IPOSIX_REGEX, field, term)
    # return Function("iregexp", field, term)

async def install_regexp_function(connection: aiosqlite.Connection):
    def regexp(expr, item):
        return re.search(expr, item) is not None

    def iregexp(expr, item):
        return re.search(expr, item, re.IGNORECASE) is not None

    await connection.create_function("regexp", 2, regexp)
    await connection.create_function("match", 2, iregexp)