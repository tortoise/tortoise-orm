from __future__ import annotations

from pypika_tortoise.enums import Comparator
from pypika_tortoise.terms import BasicCriterion, Function, Term

from tortoise.contrib.postgres.functions import ToTsQuery, ToTsVector


class Comp(Comparator):
    search = " @@ "


class SearchCriterion(BasicCriterion):
    def __init__(self, field: Term, expr: Term | Function) -> None:
        if isinstance(expr, Function):
            _expr = expr
        else:
            _expr = ToTsQuery(expr)
        super().__init__(Comp.search, ToTsVector(field), _expr)
