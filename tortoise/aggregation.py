from pypika import Table
from pypika.functions import Avg as PypikaAvg
from pypika.functions import Coalesce as PypikaCoalesce
from pypika.functions import Count as PypikaCount
from pypika.functions import Length as PypikaLength
from pypika.functions import Max as PypikaMax
from pypika.functions import Min as PypikaMin
from pypika.functions import Sum as PypikaSum
from pypika.functions import Trim as PypikaTrim
from pypika.terms import AggregateFunction

from tortoise.exceptions import ConfigurationError


class Aggregate:
    __slots__ = ("field", "default_values")

    aggregation_func = AggregateFunction

    def __init__(self, field, *default_values) -> None:
        self.field = field
        self.default_values = default_values

    def _resolve_field_for_model(self, model, field: str, *default_values) -> dict:
        field_split = field.split("__")
        if not field_split[1:]:
            aggregation_joins: list = []
            if field_split[0] in model._meta.fetch_fields:
                related_field = model._meta.fields_map[field_split[0]]
                join = (Table(model._meta.table), field_split[0], related_field)
                aggregation_joins.append(join)
                aggregation_field = self.aggregation_func(
                    Table(related_field.field_type._meta.table).id, *default_values
                )
            else:
                aggregation_field = self.aggregation_func(
                    getattr(Table(model._meta.table), field_split[0]), *default_values
                )
            return {"joins": aggregation_joins, "field": aggregation_field}

        if field_split[0] not in model._meta.fetch_fields:
            raise ConfigurationError(f"{field} not resolvable")
        related_field = model._meta.fields_map[field_split[0]]
        join = (Table(model._meta.table), field_split[0], related_field)
        aggregation = self._resolve_field_for_model(
            related_field.field_type, "__".join(field_split[1:]), *default_values
        )
        aggregation["joins"].append(join)
        return aggregation

    def resolve(self, model) -> dict:
        aggregation = self._resolve_field_for_model(model, self.field, *self.default_values)
        aggregation["joins"] = reversed(aggregation["joins"])
        return aggregation


class Count(Aggregate):
    aggregation_func = PypikaCount


class Sum(Aggregate):
    aggregation_func = PypikaSum


class Max(Aggregate):
    aggregation_func = PypikaMax


class Min(Aggregate):
    aggregation_func = PypikaMin


class Avg(Aggregate):
    aggregation_func = PypikaAvg


class Trim(Aggregate):
    aggregation_func = PypikaTrim


class Length(Aggregate):
    aggregation_func = PypikaLength


class Coalesce(Aggregate):
    aggregation_func = PypikaCoalesce
