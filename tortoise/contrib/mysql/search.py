from enum import Enum
from typing import Any, Optional

from pypika.enums import Comparator
from pypika.terms import BasicCriterion
from pypika.terms import Function as PypikaFunction
from pypika.terms import Term


class Comp(Comparator):
    search = " "


class Mode(Enum):
    NATURAL_LANGUAGE_MODE = "IN NATURAL LANGUAGE MODE"
    NATURAL_LANGUAGE_MODE_WITH_QUERY_EXPRESSION = "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
    BOOL_MODE = "IN BOOLEAN MODE"
    WITH_QUERY_EXPRESSION = "WITH QUERY EXPANSION"


class Match(PypikaFunction):
    def __init__(self, *columns: Term) -> None:
        super(Match, self).__init__("MATCH", *columns)


class Against(PypikaFunction):
    def __init__(self, expr: Term, mode: Optional[Mode] = None) -> None:
        super(Against, self).__init__("AGAINST", expr)
        self.mode = mode

    def get_special_params_sql(self, **kwargs: Any) -> Any:
        if not self.mode:
            return ""
        return self.mode.value


class SearchCriterion(BasicCriterion):
    """
    Only support for CharField, TextField with full search indexes.
    """

    def __init__(self, *columns: Term, expr: Term, mode: Optional[Mode] = None) -> None:
        super().__init__(Comp.search, Match(*columns), Against(expr, mode))
