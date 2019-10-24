import warnings

from pypika.functions import Avg as PypikaAvg
from pypika.functions import Count as PypikaCount
from pypika.functions import Max as PypikaMax
from pypika.functions import Min as PypikaMin
from pypika.functions import Sum as PypikaSum
from pypika.terms import AggregateFunction

from tortoise.functions import Function


class Aggregate(Function):
    database_func = AggregateFunction


class Count(Aggregate):
    database_func = PypikaCount


class Sum(Aggregate):
    database_func = PypikaSum


class Max(Aggregate):
    database_func = PypikaMax


class Min(Aggregate):
    database_func = PypikaMin


class Avg(Aggregate):
    database_func = PypikaAvg


warnings.warn("Trim, Length, Coalesce have been moved to tortoise.functions", DeprecationWarning)
