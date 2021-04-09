from pypika.enums import Comparator
from pypika.terms import BasicCriterion, Term

from tortoise.contrib.postgres.functions import ToTsQuery, ToTsVector


class Comp(Comparator):
    search = "@@"


class SearchCriterion(BasicCriterion):
    def __init__(self, *columns: Term, expr: Term):
        super().__init__(Comp.search, ToTsVector(*columns), ToTsQuery(expr))
