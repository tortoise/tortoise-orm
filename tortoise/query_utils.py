from pypika import Table


class Q:
    AND = 'AND'
    OR = 'OR'

    def __init__(self, *args, join_type=AND, **kwargs):
        assert bool(args) != bool(kwargs), 'you can pass only other Q nodes or filter kwargs in one Q node'
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

    def resolve_filters(self, model, filter_kwargs):
        table = Table(model._meta.table)
        for key, value in filter_kwargs.items():
            param = model._meta.filters[key]
            if param.get('table'):
                self._filter_from_related_table(table, param, value)
            else:
                self.query = self.query.where(param['operator'](getattr(table, param['field']), value))

    def resolve_for_model(self, model):
        criterion = None
        table = Table(model._meta.table)
        required_joins = []
        if self.filters:
            for key, value in self.filters.items():
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
        else:
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
