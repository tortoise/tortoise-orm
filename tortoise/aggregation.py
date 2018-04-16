from pypika import Table
from pypika.functions import Count as PypikaCount


class Aggregate:
    pass


class Count(Aggregate):
    def __init__(self, field):
        self.field = field

    def _resolve_field_for_model(self, field, model):
        field_split = self.field.split('__')
        if not field_split[1:]:
            aggregation = {
                'joins': [],
                'field': None,
            }
            if field_split[0] in model._meta.fetch_fields:
                related_field = model._meta.fields_map[field_split[0]]
                join = (Table(model._meta.table), field_split[0], related_field)
                aggregation['joins'].append(join)
                aggregation['field'] = PypikaCount(Table(related_field.type._meta.table).id)
            else:
                aggregation['field'] = PypikaCount(getattr(Table(model._meta.table), field_split[0]))
            return aggregation
        else:
            assert field_split[0] in model._meta.fetch_fields
            related_field = model._meta.fields_map[field_split[0]]
            join = (Table(model._meta.table), field_split[0], related_field)
            aggregation = self._resolve_field_for_model(field_split[:1], related_field.type)
            aggregation['joins'] += join
            return aggregation

    def resolve_for_model(self, model):
        aggregation = self._resolve_field_for_model(self.field, model)
        aggregation['joins'] = reversed(aggregation['joins'])
        return aggregation
