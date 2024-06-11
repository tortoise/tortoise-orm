from typing import Union

from pypika.enums import Comparator
from pypika.terms import BasicCriterion, Function, Term

from tortoise.contrib.postgres.functions import ToTsQuery, ToTsVector


class Comp(Comparator):  # type: ignore
    search = " @@ "


class SearchCriterion(BasicCriterion):  # type: ignore
    def __init__(self, field: Term, expr: Union[Term, Function]):
        if isinstance(expr, Function):
            _expr = expr
        else:
            _expr = ToTsQuery(expr)
        super().__init__(Comp.search, ToTsVector(field), _expr)
