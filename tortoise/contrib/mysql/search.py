from enum import Enum
from typing import Any, Optional

from pypika.enums import Comparator
from pypika.terms import BasicCriterion, Term
from pypika.terms import Function as PypikaFunction


class Comp(Comparator):  # type: ignore
    search = " "


class Mode(Enum):
    NATURAL_LANGUAGE_MODE = "IN NATURAL LANGUAGE MODE"
    NATURAL_LANGUAGE_MODE_WITH_QUERY_EXPRESSION = "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
    BOOL_MODE = "IN BOOLEAN MODE"
    WITH_QUERY_EXPRESSION = "WITH QUERY EXPANSION"


class Match(PypikaFunction):  # type: ignore
    def __init__(self, *columns: Term):
        super(Match, self).__init__("MATCH", *columns)


class Against(PypikaFunction):  # type: ignore
    def __init__(self, expr: Term, mode: Optional[Mode] = None):
        super(Against, self).__init__("AGAINST", expr)
        self.mode = mode

    def get_special_params_sql(self, **kwargs: Any) -> Any:
        if not self.mode:
            return ""
        return self.mode.value


class SearchCriterion(BasicCriterion):  # type: ignore
    """
    Only support for CharField, TextField with full search indexes.
    """

    def __init__(self, *columns: Term, expr: Term, mode: Optional[Mode] = None):
        super().__init__(Comp.search, Match(*columns), Against(expr, mode))
