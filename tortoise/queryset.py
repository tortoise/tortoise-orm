from pypika import PostgreSQLQuery as Query, Table, Order, JoinType
from pypika.functions import Count

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.exceptions import UnknownFilterParameter
from tortoise.query_utils import Q
from tortoise.utils import AsyncIteratorWrapper


class AwaitableQuery:
    def __init__(self):
        self._joined_tables = []
        self.query = None

    def _filter_from_related_table(self, table, param, value):
        if param['table'] not in self._joined_tables:
            self.query = self.query.join(param['table'], how=JoinType.left_outer).on(
                table.id == getattr(param['table'], param['backward_key'])
            )
        self.query = self.query.where(param['operator'](getattr(param['table'], param['field']), value))

    def resolve_filters(self, model, filter_kwargs, q_objects):
        table = Table(model._meta.table)
        for node in q_objects:
            criterion, required_joins = node.resolve_for_model(model)
            for join in required_joins:
                if join[0] not in self._joined_tables:
                    self.query = self.query.join(join[0], how=JoinType.left_outer).on(join[1])
                    self._joined_tables.append(join)
            self.query = self.query.where(criterion)
        for key, value in filter_kwargs.items():
            param = model._meta.filters[key]
            if param.get('table'):
                self._filter_from_related_table(table, param, value)
            else:
                self.query = self.query.where(param['operator'](getattr(table, param['field']), value))

    def __await__(self):
        return self._execute().__await__()

    async def _execute(self):
        raise NotImplementedError()


class QuerySet(AwaitableQuery):
    def __init__(self, model):
        super().__init__()
        self.fields = model._meta.db_fields
        self.model = model
        self.query = Query.from_(model._meta.table)
        self._prefetch_map = {}
        self._prefetch_queries = {}
        self._single = False
        self._count = False
        self._db = self.model._meta.db
        self._table = Table(self.model._meta.table)
        self._limit = None
        self._offset = None
        self._filter_kwargs = {}
        self._orderings = []
        self._joined_tables = []
        self._q_objects_for_resolve = []
        self._distinct = False

    def filter(self, *args, **kwargs):
        for arg in args:
            assert isinstance(arg, Q)
            self._q_objects_for_resolve.append(arg)
        for key, value in kwargs.items():
            if key in self.model._meta.filters:
                self._filter_kwargs[key] = value
            else:
                raise UnknownFilterParameter()
        return self

    def order_by(self, *orderings):
        new_ordering = []
        for ordering in orderings:
            order_type = Order.asc
            if ordering[0] == '-':
                field_name = ordering[1:]
                order_type = Order.desc
            else:
                field_name = ordering

            assert field_name in self.model._meta.fields, (
                'Unknown field {} for model {}'.format(
                    field_name,
                    self.model.__name__,
                )
            )
            new_ordering.append((field_name, order_type))
        self._orderings = new_ordering
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def offset(self, offset):
        self._offset = offset
        return self

    def distinct(self):
        self._distinct = True

    def values_list(self, *fields, flat=False):
        return ValuesListQuery(
            db=self._db,
            model=self.model,
            filter_kwargs=self._filter_kwargs,
            table=self._table,
            q_objects=self._q_objects_for_resolve,
            flat=flat,
            fields=fields,
            distinct=self._distinct,
            limit=self._limit,
            offset=self._offset,
            orderings=self._orderings,
        )

    def values(self, *fields):
        return ValuesQuery(
            db=self._db,
            model=self.model,
            filter_kwargs=self._filter_kwargs,
            table=self._table,
            q_objects=self._q_objects_for_resolve,
            fields=fields,
            distinct=self._distinct,
            limit=self._limit,
            offset=self._offset,
            orderings=self._orderings,
        )

    def delete(self):
        return DeleteQuery(
            db=self._db,
            model=self.model,
            filter_kwargs=self._filter_kwargs,
            table=self._table,
            q_objects=self._q_objects_for_resolve,
        )

    def update(self, **kwargs):
        return UpdateQuery(
            db=self._db,
            model=self.model,
            filter_kwargs=self._filter_kwargs,
            table=self._table,
            update_kwargs=kwargs,
            q_objects=self._q_objects_for_resolve,
        )

    def count(self):
        return CountQuery(
            db=self._db,
            model=self.model,
            filter_kwargs=self._filter_kwargs,
            table=self._table,
            q_objects=self._q_objects_for_resolve,
        )

    def all(self):
        return self

    def first(self):
        self.query = self.query.limit(1)
        self._single = True
        return self

    def prefetch_related(self, *args):
        self._prefetch_map = {}

        for relation in args:
            relation_split = relation.split('__')
            first_level_field = relation_split[0]
            assert (
                first_level_field in self.model._meta.fetch_fields
            ), 'relation {} for {} not found'.format(
                first_level_field,
                self.model._meta.table
            )
            if first_level_field not in self._prefetch_map.keys():
                self._prefetch_map[first_level_field] = set()
            forwarded_prefetch = '__'.join(relation_split[1:])
            if forwarded_prefetch:
                self._prefetch_map[first_level_field].add(forwarded_prefetch)
        return self

    def using_db(self, _db: BaseDBAsyncClient):
        self._db = _db
        return self

    def _make_query(self):
        self.query = self._db.query_class.from_(self._table).select(*self.fields)
        self.resolve_filters(self.model, self._filter_kwargs, self._q_objects_for_resolve)
        if self._limit:
            self.query = self.query.limit(self._limit)
        if self._offset:
            self.query = self.query.offset(self._offset)
        if self._distinct:
            self.query = self.query.distinct()
        for ordering in self._orderings:
            self.query = self.query.orderby(ordering[0], order=ordering[1])
        return self.query

    async def _execute(self):
        self.query = self._make_query()
        instance_list = await self._db.executor_class(
            model=self.model,
            db=self._db,
            prefetch_map=self._prefetch_map,
        ).execute_select(self.query)
        if not instance_list:
            if self._single:
                return None
            return []
        elif self._single:
            return instance_list[0]
        return instance_list

    async def __aiter__(self):
        result = await self
        return AsyncIteratorWrapper(result)


class UpdateQuery(AwaitableQuery):
    def __init__(self, model, filter_kwargs, update_kwargs, table, db, q_objects):
        super().__init__()
        self.query = db.query_class.update(table)
        self.resolve_filters(model, filter_kwargs, q_objects)

        for key, value in update_kwargs.items():
            self.query = self.query.set(key, value)
        self._db = db

    async def _execute(self):
        await self._db.execute_query(str(self.query))


class DeleteQuery(AwaitableQuery):
    def __init__(self, model, filter_kwargs, table, db, q_objects):
        super().__init__()
        self.query = db.query_class.from_(table)
        self.resolve_filters(model, filter_kwargs, q_objects)
        self.query = self.query.delete()
        self._db = db

    async def _execute(self):
        await self._db.execute_query(str(self.query))


class CountQuery(AwaitableQuery):
    def __init__(self, model, filter_kwargs, table, db, q_objects):
        super().__init__()
        self.query = db.query_class.from_(table)
        self.resolve_filters(model, filter_kwargs, q_objects)
        self.query = self.query.select(Count(table.star))
        self._db = db

    async def _execute(self):
        result = await self._db.execute_query(str(self.query))
        return result[0][0]


class ValuesListQuery(AwaitableQuery):
    def __init__(self, model, filter_kwargs, table, db, q_objects, fields, limit, offset, distinct,
                 orderings, flat):
        super().__init__()
        assert (len(fields) == 1) == flat, 'You can flat value_list only if contains one field'
        for field in fields:
            assert field in model._meta.fields_db_projection
        self._db = db
        self.query = self._db.query_class.from_(table).select(*fields)
        self.resolve_filters(model, filter_kwargs, q_objects)
        if limit:
            self.query = self.query.limit(limit)
        if offset:
            self.query = self.query.offset(offset)
        if distinct:
            self.query = self.query.distinct()
        for ordering in orderings:
            self.query = self.query.orderby(ordering[0], order=ordering[1])
        self.flat = flat
        self.fields = fields
        self.model = model

    async def _execute(self):
        result = await self._db.execute_query(str(self.query))
        if self.flat:
            db_field = self.model._meta.fields_db_projection[self.fields[0]]
            return [entry[db_field] for entry in result]
        values_list = []
        for entry in result:
            values = []
            for field in self.fields:
                db_field = self.model._meta.fields_db_projection[field]
                values.append(entry[db_field])
            values_list.append(values)
        return values_list


class ValuesQuery(AwaitableQuery):
    def __init__(self, model, filter_kwargs, table, db, q_objects, fields, limit, offset, distinct,
                 orderings):
        super().__init__()
        for field in fields:
            assert field in model._meta.fields_db_projection
        self._db = db
        self.query = self._db.query_class.from_(table).select(*fields)
        self.resolve_filters(model, filter_kwargs, q_objects)
        if limit:
            self.query = self.query.limit(limit)
        if offset:
            self.query = self.query.offset(offset)
        if distinct:
            self.query = self.query.distinct()
        for ordering in orderings:
            self.query = self.query.orderby(ordering[0], order=ordering[1])
        self.fields = fields
        self.model = model

    async def _execute(self):
        return await self._db.execute_query(str(self.query))
