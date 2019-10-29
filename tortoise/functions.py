from pypika import Table
from pypika.functions import Avg as PypikaAvg
from pypika.functions import Coalesce as PypikaCoalesce
from pypika.functions import Count as PypikaCount
from pypika.functions import Length as PypikaLength
from pypika.functions import Lower as PypikaLower
from pypika.functions import Max as PypikaMax
from pypika.functions import Min as PypikaMin
from pypika.functions import Sum as PypikaSum
from pypika.functions import Trim as PypikaTrim
from pypika.functions import Upper as PypikaUpper
from pypika.terms import AggregateFunction
from pypika.terms import Function as BaseFunction

from tortoise.exceptions import ConfigurationError

##############################################################################
# Base
##############################################################################


class Function:
    __slots__ = ("field", "default_values")

    database_func = BaseFunction

    def __init__(self, field, *default_values) -> None:
        self.field = field
        self.default_values = default_values

    def _resolve_field_for_model(self, model, field: str, *default_values) -> dict:
        field_split = field.split("__")
        if not field_split[1:]:
            function_joins: list = []
            if field_split[0] in model._meta.fetch_fields:
                related_field = model._meta.fields_map[field_split[0]]
                join = (Table(model._meta.table), field_split[0], related_field)
                function_joins.append(join)
                function_field = self.database_func(
                    Table(related_field.field_type._meta.table).id, *default_values
                )
            else:
                function_field = self.database_func(
                    getattr(Table(model._meta.table), field_split[0]), *default_values
                )
            return {"joins": function_joins, "field": function_field}

        if field_split[0] not in model._meta.fetch_fields:
            raise ConfigurationError(f"{field} not resolvable")
        related_field = model._meta.fields_map[field_split[0]]
        join = (Table(model._meta.table), field_split[0], related_field)
        function = self._resolve_field_for_model(
            related_field.field_type, "__".join(field_split[1:]), *default_values
        )
        function["joins"].append(join)
        return function

    def resolve(self, model) -> dict:
        function = self._resolve_field_for_model(model, self.field, *self.default_values)
        function["joins"] = reversed(function["joins"])
        return function


class Aggregate(Function):
    database_func = AggregateFunction


##############################################################################
# Standard functions
##############################################################################


class Trim(Function):
    database_func = PypikaTrim


class Length(Function):
    database_func = PypikaLength


class Coalesce(Function):
    database_func = PypikaCoalesce


class Lower(Function):
    database_func = PypikaLower


class Upper(Function):
    database_func = PypikaUpper


##############################################################################
# Aggregate functions
##############################################################################


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
