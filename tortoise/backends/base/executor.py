from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple, Type  # noqa

from pypika import JoinType, Table

from tortoise import fields
from tortoise.exceptions import OperationalError
from tortoise.query_utils import QueryModifier

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model

INSERT_CACHE = {}  # type: Dict[str, Tuple[list, str, Dict[str, Callable]]]


class BaseExecutor:
    TO_DB_OVERRIDE = {}  # type: Dict[Type[fields.Field], Callable]
    FILTER_FUNC_OVERRIDE = {}  # type: Dict[Callable, Callable]
    EXPLAIN_PREFIX = "EXPLAIN"

    def __init__(self, model, db=None, prefetch_map=None, prefetch_queries=None):
        self.model = model
        self.db = db
        self.prefetch_map = prefetch_map if prefetch_map else {}
        self._prefetch_queries = prefetch_queries if prefetch_queries else {}

        key = "{}:{}".format(self.db.connection_name, self.model._meta.table)
        if key not in INSERT_CACHE:
            self.regular_columns, columns = self._prepare_insert_columns()
            self.query = self._prepare_insert_statement(columns)

            self.column_map = {}  # type: Dict[str, Callable]
            for column in self.regular_columns:
                field_object = self.model._meta.fields_map[column]
                if field_object.__class__ in self.TO_DB_OVERRIDE:
                    func = partial(self.TO_DB_OVERRIDE[field_object.__class__], field_object)
                else:
                    func = field_object.to_db_value
                self.column_map[column] = func

            INSERT_CACHE[key] = self.regular_columns, self.query, self.column_map
        else:
            self.regular_columns, self.query, self.column_map = INSERT_CACHE[key]

    async def execute_explain(self, query) -> Any:
        sql = " ".join(((self.EXPLAIN_PREFIX, query.get_sql())))
        return await self.db.execute_query(sql)

    async def execute_select(self, query, custom_fields: Optional[list] = None) -> list:
        raw_results = await self.db.execute_query(query.get_sql())
        instance_list = []
        for row in raw_results:
            instance = self.model(_from_db=True, **row)
            if custom_fields:
                for field in custom_fields:
                    setattr(instance, field, row[field])
            instance_list.append(instance)
        await self._execute_prefetch_queries(instance_list)
        return instance_list

    def _prepare_insert_columns(self) -> Tuple[List[str], List[str]]:
        regular_columns = []
        for column in self.model._meta.fields_db_projection.keys():
            field_object = self.model._meta.fields_map[column]
            if not field_object.generated:
                regular_columns.append(column)
        result_columns = [self.model._meta.fields_db_projection[c] for c in regular_columns]
        return regular_columns, result_columns

    @classmethod
    def _field_to_db(cls, field_object: fields.Field, attr: Any, instance) -> Any:
        if field_object.__class__ in cls.TO_DB_OVERRIDE:
            return cls.TO_DB_OVERRIDE[field_object.__class__](field_object, attr, instance)
        return field_object.to_db_value(attr, instance)

    def _prepare_insert_statement(self, columns: List[str]) -> str:
        # Insert should implement returning new id to saved object
        # Each db has it's own methods for it, so each implementation should
        # go to descendant executors
        raise NotImplementedError()  # pragma: nocoverage

    async def _process_insert_result(self, instance: "Model", results: Any):
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_insert(self, instance):
        values = [
            self.column_map[column](getattr(instance, column), instance)
            for column in self.regular_columns
        ]
        insert_result = await self.db.execute_insert(self.query, values)
        await self._process_insert_result(instance, insert_result)
        return instance

    async def execute_bulk_insert(self, instances):
        values_lists = [
            [
                self.column_map[column](getattr(instance, column), instance)
                for column in self.regular_columns
            ]
            for instance in instances
        ]
        await self.db.execute_many(self.query, values_lists)

    async def execute_update(self, instance):
        table = Table(self.model._meta.table)
        query = self.db.query_class.update(table)
        for field, db_field in self.model._meta.fields_db_projection.items():
            field_object = self.model._meta.fields_map[field]
            if not field_object.generated:
                query = query.set(
                    db_field, self.column_map[field](getattr(instance, field), instance)
                )
        query = query.where(
            getattr(table, self.model._meta.db_pk_field)
            == self.model._meta.pk.to_db_value(instance.pk, instance)
        )
        await self.db.execute_query(query.get_sql())
        return instance

    async def execute_delete(self, instance):
        table = Table(self.model._meta.table)
        query = self.model._meta.basequery.where(
            getattr(table, self.model._meta.db_pk_field)
            == self.model._meta.pk.to_db_value(instance.pk, instance)
        ).delete()
        await self.db.execute_query(query.get_sql())
        return instance

    async def _prefetch_reverse_relation(
        self, instance_list: list, field: str, related_query
    ) -> list:
        instance_id_set = {instance.pk for instance in instance_list}  # type: Set[Any]
        backward_relation_manager = getattr(self.model, field)
        relation_field = backward_relation_manager.relation_field

        related_object_list = await related_query.filter(
            **{"{}__in".format(relation_field): list(instance_id_set)}
        )

        related_object_map = {}  # type: Dict[str, list]
        for entry in related_object_list:
            object_id = getattr(entry, relation_field)
            if object_id in related_object_map.keys():
                related_object_map[object_id].append(entry)
            else:
                related_object_map[object_id] = [entry]
        for instance in instance_list:
            relation_container = getattr(instance, field)
            relation_container._set_result_for_query(related_object_map.get(instance.pk, []))
        return instance_list

    async def _prefetch_m2m_relation(self, instance_list: list, field: str, related_query) -> list:
        instance_id_set = {instance.pk for instance in instance_list}  # type: Set[Any]

        field_object = self.model._meta.fields_map[field]

        through_table = Table(field_object.through)

        subquery = (
            self.db.query_class.from_(through_table)
            .select(
                getattr(through_table, field_object.backward_key).as_("_backward_relation_key"),
                getattr(through_table, field_object.forward_key).as_("_forward_relation_key"),
            )
            .where(getattr(through_table, field_object.backward_key).isin(instance_id_set))
        )

        related_query_table = Table(related_query.model._meta.table)
        related_pk_field = related_query.model._meta.db_pk_field
        query = (
            related_query.query.join(subquery)
            .on(subquery._forward_relation_key == getattr(related_query_table, related_pk_field))
            .select(
                subquery._backward_relation_key.as_("_backward_relation_key"),
                *[getattr(related_query_table, field).as_(field) for field in related_query.fields],
            )
        )

        if related_query._q_objects:
            joined_tables = []  # type: List[Table]
            modifier = QueryModifier()
            for node in related_query._q_objects:
                modifier &= node.resolve(
                    model=related_query.model,
                    annotations=related_query._annotations,
                    custom_filters=related_query._custom_filters,
                )

            where_criterion, joins, having_criterion = modifier.get_query_modifiers()
            for join in joins:
                if join[0] not in joined_tables:
                    query = query.join(join[0], how=JoinType.left_outer).on(join[1])
                    joined_tables.append(join[0])

            if where_criterion:
                query = query.where(where_criterion)

            if having_criterion:
                query = query.having(having_criterion)

        raw_results = await self.db.execute_query(query.get_sql())
        relations = {
            (
                self.model._meta.pk.to_python_value(e["_backward_relation_key"]),
                field_object.type._meta.pk.to_python_value(e[related_pk_field]),
            )
            for e in raw_results
        }
        related_object_list = [related_query.model(_from_db=True, **e) for e in raw_results]
        await self.__class__(
            model=related_query.model, db=self.db, prefetch_map=related_query._prefetch_map
        ).fetch_for_list(related_object_list)
        related_object_map = {e.pk: e for e in related_object_list}
        relation_map = {}  # type: Dict[str, list]

        for object_id, related_object_id in relations:
            if object_id not in relation_map:
                relation_map[object_id] = []
            relation_map[object_id].append(related_object_map[related_object_id])

        for instance in instance_list:
            relation_container = getattr(instance, field)
            relation_container._set_result_for_query(relation_map.get(instance.pk, []))
        return instance_list

    async def _prefetch_direct_relation(
        self, instance_list: list, field: str, related_query
    ) -> list:
        related_objects_for_fetch = set()
        relation_key_field = "{}_id".format(field)
        for instance in instance_list:
            if getattr(instance, relation_key_field):
                related_objects_for_fetch.add(getattr(instance, relation_key_field))
        if related_objects_for_fetch:
            related_object_list = await related_query.filter(pk__in=list(related_objects_for_fetch))
            related_object_map = {obj.pk: obj for obj in related_object_list}
            for instance in instance_list:
                setattr(
                    instance, field, related_object_map.get(getattr(instance, relation_key_field))
                )
        return instance_list

    def _make_prefetch_queries(self) -> None:
        for field, forwarded_prefetches in self.prefetch_map.items():
            if field in self._prefetch_queries:
                related_query = self._prefetch_queries.get(field)
            else:
                related_model_field = self.model._meta.fields_map.get(field)
                related_model = related_model_field.type
                related_query = related_model.all().using_db(self.db)
            if forwarded_prefetches:
                related_query = related_query.prefetch_related(*forwarded_prefetches)
            self._prefetch_queries[field] = related_query

    async def _do_prefetch(self, instance_id_list: list, field: str, related_query) -> list:
        if isinstance(getattr(self.model, field), fields.BackwardFKRelation):
            return await self._prefetch_reverse_relation(instance_id_list, field, related_query)
        elif isinstance(getattr(self.model, field), fields.ManyToManyField):
            return await self._prefetch_m2m_relation(instance_id_list, field, related_query)
        else:
            return await self._prefetch_direct_relation(instance_id_list, field, related_query)

    async def _execute_prefetch_queries(self, instance_list: list) -> list:
        if instance_list and (self.prefetch_map or self._prefetch_queries):
            self._make_prefetch_queries()
            for field, related_query in self._prefetch_queries.items():
                await self._do_prefetch(instance_list, field, related_query)
        return instance_list

    async def fetch_for_list(self, instance_list: list, *args) -> list:
        self.prefetch_map = {}
        for relation in args:
            relation_split = relation.split("__")
            first_level_field = relation_split[0]
            if first_level_field not in self.model._meta.fetch_fields:
                raise OperationalError(
                    "relation {} for {} not found".format(first_level_field, self.model._meta.table)
                )
            if first_level_field not in self.prefetch_map.keys():
                self.prefetch_map[first_level_field] = set()
            forwarded_prefetch = "__".join(relation_split[1:])
            if forwarded_prefetch:
                self.prefetch_map[first_level_field].add(forwarded_prefetch)
        await self._execute_prefetch_queries(instance_list)
        return instance_list

    @classmethod
    def get_overridden_filter_func(cls, filter_func: Callable) -> Optional[Callable]:
        return cls.FILTER_FUNC_OVERRIDE.get(filter_func)
