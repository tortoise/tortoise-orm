from enum import Enum
from typing import Any, Set

from pypika.enums import Comparator
from pypika.terms import BasicCriterion, Function


class Comp(Comparator):
    search = " "


class Mode(Enum):
    NATURAL_LANGUAGE_MODE = "IN NATURAL LANGUAGE MODE"
    NATURAL_LANGUAGE_MODE_WITH_QUERY_EXPRESSION = "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION"
    BOOL_MODE = "IN BOOLEAN MODE"
    WITH_QUERY_EXPRESSION = "WITH QUERY EXPANSION"


class Match(Function):
    def __init__(self, columns: Set[str], **kwargs):
        super(Match, self).__init__("MATCH", ", ".join(columns), **kwargs)


class Against(Function):
    def __init__(self, expr: str, mode: Mode, **kwargs):
        super(Against, self).__init__("AGAINST", expr, **kwargs)
        self.mode = mode

    def get_special_params_sql(self, **kwargs: Any) -> Any:
        return self.mode.value


class Search(BasicCriterion):
    def __init__(self, columns: Set[str], expr: str, mode: Mode = ""):
        super().__init__(Comp.search, Match(columns), Against(expr, mode))
