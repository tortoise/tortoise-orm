from pypika.terms import Term, BasicCriterion
from pypika.enums import Comparator

class PostgresRegexMatching(Comparator):
    posix_regex = " ~ "

def postgres_posix_regex(field: Term, value: str):
    return BasicCriterion(PostgresRegexMatching.posix_regex, field, field.wrap_constant(value))