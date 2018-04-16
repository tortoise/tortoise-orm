from pypika import Table

from tortoise import fields


class Q:
    AND = 'AND'
    OR = 'OR'

    def __init__(self, *args, join_type=AND, **kwargs):
        assert not (bool(args) and bool(kwargs)), 'you can pass only Q nodes or filter kwargs in one Q node'
        assert all(isinstance(node, Q) for node in args)
        self.children = args
        self.filters = kwargs
        assert join_type in {self.AND, self.OR}
        self.join_type = join_type

    def __and__(self, other):
        assert isinstance(other, Q)
        return Q(self, other, join_type=self.AND)

    def __or__(self, other):
        assert isinstance(other, Q)
        return Q(self, other, join_type=self.OR)

    def _get_from_related_table(self, table, param, value):
        join = (param['table'], table.id == getattr(param['table'], param['backward_key']))
        criterion = param['operator'](getattr(param['table'], param['field']), value)
        return criterion, join

    def _resolve_nested_filter(self, model, key, value):
        table = Table(model._meta.table)
        required_joins = []
        related_field_name = key.split('__')[0]
        related_field = model._meta.fields_map[related_field_name]
        if isinstance(related_field, fields.ManyToManyField):
            related_table = Table(related_field.type._meta.table)
            through_table = Table(related_field.through)
            required_joins.append((
                through_table,
                table.id == getattr(through_table, related_field.backward_key)
            ))
            required_joins.append((
                related_table,
                getattr(through_table, related_field.forward_key) == related_table.id
            ))
        elif isinstance(related_field, fields.BackwardFKRelation):
            related_table = Table(related_field.type._meta.table)
            required_joins.append((
                related_table,
                table.id == getattr(related_table, related_field.relation_field)
            ))
        else:
            related_table = Table(related_field.type._meta.table)
            required_joins.append((
                related_table,
                related_table.id == getattr(table, '{}_id'.format(related_field_name))
            ))

        new_criterion, new_joins = Q(
            **{'__'.join(key.split('__')[1:]): value}
        ).resolve_for_model(related_field.type)

        required_joins += new_joins
        return new_criterion, required_joins

    def _resolve_kwargs(self, model):
        criterion = None
        table = Table(model._meta.table)
        required_joins = []
        for key, value in self.filters.items():
            if key not in model._meta.filters and key.split('__')[0] in model._meta.fetch_fields:
                new_criterion, new_joins = self._resolve_nested_filter(model, key, value)
                required_joins += new_joins
            else:
                param = model._meta.filters[key]
                if param.get('table'):
                    new_criterion, join = self._get_from_related_table(param['table'], param, value)
                    required_joins.append(join)
                else:
                    new_criterion = param['operator'](getattr(table, param['field']), value)
            if not criterion:
                criterion = new_criterion
            else:
                if self.join_type == self.AND:
                    criterion &= new_criterion
                else:
                    criterion |= new_criterion
        return criterion, required_joins

    def _resolve_children(self, model):
        criterion = None
        required_joins = []
        for node in self.children:
            new_criterion, children_joins = node.resolve_for_model(model)
            required_joins += children_joins
            if not criterion:
                criterion = new_criterion
            else:
                if self.join_type == self.AND:
                    criterion &= new_criterion
                else:
                    criterion |= new_criterion
        return criterion, required_joins

    def resolve_for_model(self, model):
        if self.filters:
            return self._resolve_kwargs(model)
        else:
            return self._resolve_children(model)


class Prefetch:
    def __init__(self, relation, queryset):
        self.relation = relation
        self.queryset = queryset

    def resolve_for_queryset(self, queryset):
        relation_split = self.relation.split('__')
        first_level_field = relation_split[0]
        assert (
                first_level_field in queryset.model._meta.fetch_fields
        ), 'relation {} for {} not found'.format(
            first_level_field,
            queryset.model._meta.table
        )
        forwarded_prefetch = '__'.join(relation_split[1:])
        if forwarded_prefetch:
            if first_level_field not in queryset._prefetch_map.keys():
                queryset._prefetch_map[first_level_field] = set()
            queryset._prefetch_map[first_level_field].add(Prefetch(forwarded_prefetch, self.queryset))
        else:
            queryset._prefetch_queries[first_level_field] = self.queryset
