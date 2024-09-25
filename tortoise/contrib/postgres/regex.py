from pypika.terms import Term, BasicCriterion


def posix_regex(field: Term, value: str):
    return BasicCriterion(" ~ ", field, value)