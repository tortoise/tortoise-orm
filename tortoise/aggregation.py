from pypika import Table
from pypika.functions import Avg as PypikaAvg
from pypika.functions import Count as PypikaCount
from pypika.functions import Max as PypikaMax
from pypika.functions import Min as PypikaMin
from pypika.functions import Sum as PypikaSum
from pypika.terms import AggregateFunction

from tortoise.exceptions import ConfigurationError


class Aggregate:
    aggregation_func = AggregateFunction

    def __init__(self, field) -> None:
        self.field = field

    def _resolve_field_for_model(self, field: str, model) -> dict:
        field_split = field.split('__')
        if not field_split[1:]:
            aggregation_joins = []  # type: list
            if field_split[0] in model._meta.fetch_fields:
                related_field = model._meta.fields_map[field_split[0]]
                join = (Table(model._meta.table), field_split[0], related_field)
                aggregation_joins.append(join)
                aggregation_field = self.aggregation_func(
                    Table(related_field.type._meta.table).id
                )
            else:
                aggregation_field = self.aggregation_func(
                    getattr(Table(model._meta.table), field_split[0])
                )
            return {
                'joins': aggregation_joins,
                'field': aggregation_field,
            }
        else:
            if field_split[0] not in model._meta.fetch_fields:
                raise ConfigurationError('{} not resolvable'.format(field))
            related_field = model._meta.fields_map[field_split[0]]
            join = (Table(model._meta.table), field_split[0], related_field)
            aggregation = self._resolve_field_for_model(
                '__'.join(field_split[1:]), related_field.type
            )
            aggregation['joins'].append(join)
            return aggregation

    def resolve_for_model(self, model) -> dict:
        aggregation = self._resolve_field_for_model(self.field, model)
        aggregation['joins'] = reversed(aggregation['joins'])
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
