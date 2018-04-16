from pypika import Table
from pypika.functions import Count as PypikaCount
from pypika.functions import Sum as PypikaSum
from pypika.functions import Min as PypikaMin
from pypika.functions import Max as PypikaMax
from pypika.functions import Avg as PypikaAvg


class Aggregate:
    aggregation_func = None

    def __init__(self, field):
        self.field = field

    def _resolve_field_for_model(self, field, model):
        field_split = field.split('__')
        if not field_split[1:]:
            aggregation = {
                'joins': [],
                'field': None,
            }
            if field_split[0] in model._meta.fetch_fields:
                related_field = model._meta.fields_map[field_split[0]]
                join = (Table(model._meta.table), field_split[0], related_field)
                aggregation['joins'].append(join)
                aggregation['field'] = self.aggregation_func(Table(related_field.type._meta.table).id)
            else:
                aggregation['field'] = self.aggregation_func(getattr(Table(model._meta.table), field_split[0]))
            return aggregation
        else:
            assert field_split[0] in model._meta.fetch_fields
            related_field = model._meta.fields_map[field_split[0]]
            join = (Table(model._meta.table), field_split[0], related_field)
            aggregation = self._resolve_field_for_model('__'.join(field_split[1:]), related_field.type)
            aggregation['joins'].append(join)
            return aggregation

    def resolve_for_model(self, model):
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
