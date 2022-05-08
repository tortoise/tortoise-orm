import asyncio
import datetime
import decimal
from copy import copy
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from pypika import JoinType, Parameter, Query, Table
from pypika.queries import QueryBuilder
from pypika.terms import ArithmeticExpression, Function

from tortoise.exceptions import OperationalError
from tortoise.expressions import F, RawSQL
from tortoise.fields.base import Field
from tortoise.fields.relational import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    ManyToManyFieldInstance,
    RelationalField,
)
from tortoise.query_utils import QueryModifier
from tortoise.utils import chunk

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import BaseDBAsyncClient
    from tortoise.models import Model
    from tortoise.query_utils import Prefetch
    from tortoise.queryset import QuerySet

EXECUTOR_CACHE: Dict[
    str, Tuple[list, str, list, str, Dict[str, Callable], str, Dict[str, str]]
] = {}


class BaseExecutor:
    TO_DB_OVERRIDE: Dict[Type[Field], Callable] = {}
    FILTER_FUNC_OVERRIDE: Dict[Callable, Callable] = {}
    EXPLAIN_PREFIX: str = "EXPLAIN"
    DB_NATIVE = {bytes, str, int, float, decimal.Decimal, datetime.datetime, datetime.date}

    def __init__(
        self,
        model: "Type[Model]",
        db: "BaseDBAsyncClient",
        prefetch_map: "Optional[Dict[str, Set[Union[str, Prefetch]]]]" = None,
        prefetch_queries: Optional[Dict[str, List[Tuple[Optional[str], "QuerySet"]]]] = None,
        select_related_idx: Optional[
            List[Tuple["Type[Model]", int, str, "Type[Model]", Iterable[Optional[str]]]]
        ] = None,
    ) -> None:
        self.model = model
        self.db: "BaseDBAsyncClient" = db
        self.prefetch_map = prefetch_map or {}
        self._prefetch_queries = prefetch_queries or {}
        self.select_related_idx = select_related_idx
        key = f"{self.db.connection_name}:{self.model._meta.db_table}"
        if key not in EXECUTOR_CACHE:
            self.regular_columns, columns = self._prepare_insert_columns()
            self.insert_query = str(self._prepare_insert_statement(columns))
            self.regular_columns_all = self.regular_columns
            self.insert_query_all = self.insert_query
            if self.model._meta.generated_db_fields:
                self.regular_columns_all, columns_all = self._prepare_insert_columns(
                    include_generated=True
                )
                self.insert_query_all = str(
                    self._prepare_insert_statement(columns_all, has_generated=False)
                )

            self.column_map: Dict[str, Callable[[Any, Any], Any]] = {}
            for column in self.regular_columns_all:
                field_object = self.model._meta.fields_map[column]
                if field_object.__class__ in self.TO_DB_OVERRIDE:
                    self.column_map[column] = partial(
                        self.TO_DB_OVERRIDE[field_object.__class__], field_object
                    )
                else:
                    self.column_map[column] = field_object.to_db_value

            table = self.model._meta.basetable
            self.delete_query = str(
                self.model._meta.basequery.where(
                    table[self.model._meta.db_pk_column] == self.parameter(0)
                ).delete()
            )
            self.update_cache: Dict[str, str] = {}

            EXECUTOR_CACHE[key] = (
                self.regular_columns,
                self.insert_query,
                self.regular_columns_all,
                self.insert_query_all,
                self.column_map,
                self.delete_query,
                self.update_cache,
            )

        else:
            (
                self.regular_columns,
                self.insert_query,
                self.regular_columns_all,
                self.insert_query_all,
                self.column_map,
                self.delete_query,
                self.update_cache,
            ) = EXECUTOR_CACHE[key]

    async def execute_explain(self, query: Query) -> Any:
        sql = " ".join((self.EXPLAIN_PREFIX, query.get_sql()))
        return (await self.db.execute_query(sql))[1]

    async def execute_select(
        self, query: Union[Query, RawSQL], custom_fields: Optional[list] = None
    ) -> list:
        _, raw_results = await self.db.execute_query(query.get_sql())
        instance_list = []
        for row in raw_results:
            if self.select_related_idx:
                _, current_idx, _, _, path = self.select_related_idx[0]
                dict_row = dict(row)
                keys = list(dict_row.keys())
                values = list(dict_row.values())
                instance: "Model" = self.model._init_from_db(
                    **dict(zip(keys[:current_idx], values[:current_idx]))
                )
                instances: Dict[Any, Any] = {path: instance}
                for (
                    model,
                    index,
                    model_name,
                    parent_model,
                    full_path,
                ) in self.select_related_idx[1:]:
                    (*path, attr) = full_path
                    related_values = values[current_idx : current_idx + index]  # noqa
                    if not any(related_values):
                        obj = None
                    else:
                        obj = model._init_from_db(
                            **dict(
                                zip(
                                    map(
                                        lambda x: x.split(".")[1],
                                        keys[current_idx : current_idx + index],  # noqa
                                    ),
                                    related_values,
                                )
                            )
                        )
                    target = instances.get(tuple(path))
                    if target is not None:
                        setattr(target, f"_{attr}", obj)
                    if obj is not None:
                        instances[(*path, attr)] = obj
                    current_idx += index
            else:
                instance = self.model._init_from_db(**row)
            if custom_fields:
                for field in custom_fields:
                    setattr(instance, field, row[field])
            instance_list.append(instance)
        await self._execute_prefetch_queries(instance_list)
        return instance_list

    def _prepare_insert_columns(
        self, include_generated: bool = False
    ) -> Tuple[List[str], List[str]]:
        regular_columns = []
        for column in self.model._meta.fields_db_projection.keys():
            field_object = self.model._meta.fields_map[column]
            if include_generated or not field_object.generated:
                regular_columns.append(column)
        result_columns = [self.model._meta.fields_db_projection[c] for c in regular_columns]
        return regular_columns, result_columns

    @classmethod
    def _field_to_db(
        cls, field_object: Field, attr: Any, instance: "Union[Type[Model], Model]"
    ) -> Any:
        if field_object.__class__ in cls.TO_DB_OVERRIDE:
            return cls.TO_DB_OVERRIDE[field_object.__class__](field_object, attr, instance)
        return field_object.to_db_value(attr, instance)

    def _prepare_insert_statement(
        self, columns: Sequence[str], has_generated: bool = True, ignore_conflicts: bool = False
    ) -> QueryBuilder:
        # Insert should implement returning new id to saved object
        # Each db has it's own methods for it, so each implementation should
        # go to descendant executors
        query = (
            self.db.query_class.into(self.model._meta.basetable)
            .columns(*columns)
            .insert(*[self.parameter(i) for i in range(len(columns))])
        )
        if ignore_conflicts:
            query = query.on_conflict().do_nothing()
        return query

    async def _process_insert_result(self, instance: "Model", results: Any) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    def parameter(self, pos: int) -> Parameter:
        raise NotImplementedError()  # pragma: nocoverage

    async def execute_insert(self, instance: "Model") -> None:
        if not instance._custom_generated_pk:
            values = [
                self.column_map[field_name](getattr(instance, field_name), instance)
                for field_name in self.regular_columns
            ]
            insert_result = await self.db.execute_insert(self.insert_query, values)
            await self._process_insert_result(instance, insert_result)

        else:
            values = [
                self.column_map[field_name](getattr(instance, field_name), instance)
                for field_name in self.regular_columns_all
            ]
            await self.db.execute_insert(self.insert_query_all, values)

    async def execute_bulk_insert(
        self,
        instances: "Iterable[Model]",
        batch_size: Optional[int] = None,
    ) -> None:
        for instance_chunk in chunk(instances, batch_size):
            values_lists_all = []
            values_lists = []
            for instance in instance_chunk:
                if instance._custom_generated_pk:
                    values_lists_all.append(
                        [
                            self.column_map[field_name](getattr(instance, field_name), instance)
                            for field_name in self.regular_columns_all
                        ]
                    )
                else:
                    values_lists.append(
                        [
                            self.column_map[field_name](getattr(instance, field_name), instance)
                            for field_name in self.regular_columns
                        ]
                    )

            if values_lists_all:
                await self.db.execute_many(self.insert_query_all, values_lists_all)
            if values_lists:
                await self.db.execute_many(self.insert_query, values_lists)

    def get_update_sql(
        self,
        update_fields: Optional[Iterable[str]],
        arithmetic_or_function: Optional[Dict[str, Union[ArithmeticExpression, Function]]],
    ) -> str:
        """
        Generates the SQL for updating a model depending on provided update_fields.
        Result is cached for performance.
        """
        key = ",".join(update_fields) if update_fields else ""
        if not arithmetic_or_function and key in self.update_cache:
            return self.update_cache[key]
        arithmetic_or_function = arithmetic_or_function or {}
        table = self.model._meta.basetable
        query = self.db.query_class.update(table)
        count = 0
        for field in update_fields or self.model._meta.fields_db_projection.keys():
            db_column = self.model._meta.fields_db_projection[field]
            field_object = self.model._meta.fields_map[field]
            if not field_object.pk:
                if field not in arithmetic_or_function.keys():
                    query = query.set(db_column, self.parameter(count))
                    count += 1
                else:
                    value = F.resolver_arithmetic_expression(
                        self.model, arithmetic_or_function.get(field)
                    )[0]
                    query = query.set(db_column, value)

        query = query.where(table[self.model._meta.db_pk_column] == self.parameter(count))

        sql = query.get_sql()
        if not arithmetic_or_function:
            self.update_cache[key] = sql
        return sql

    async def execute_update(
        self, instance: "Union[Type[Model], Model]", update_fields: Optional[Iterable[str]]
    ) -> int:
        values = []
        arithmetic_or_function = {}
        for field in update_fields or self.model._meta.fields_db_projection.keys():
            if not self.model._meta.fields_map[field].pk:
                instance_field = getattr(instance, field)
                if isinstance(instance_field, (ArithmeticExpression, Function)):
                    arithmetic_or_function[field] = instance_field
                else:
                    value = self.column_map[field](instance_field, instance)
                    values.append(value)
        values.append(self.model._meta.pk.to_db_value(instance.pk, instance))
        return (
            await self.db.execute_query(
                self.get_update_sql(update_fields, arithmetic_or_function), values
            )
        )[0]

    async def execute_delete(self, instance: "Union[Type[Model], Model]") -> int:
        return (
            await self.db.execute_query(
                self.delete_query, [self.model._meta.pk.to_db_value(instance.pk, instance)]
            )
        )[0]

    async def _prefetch_reverse_relation(
        self,
        instance_list: "Iterable[Model]",
        field: str,
        related_query: Tuple[Optional[str], "QuerySet"],
    ) -> "Iterable[Model]":
        to_attr, related_query = related_query
        related_objects_for_fetch: Dict[str, list] = {}
        related_field: BackwardFKRelation = self.model._meta.fields_map[field]  # type: ignore
        related_field_name = related_field.to_field_instance.model_field_name
        relation_field = related_field.relation_field

        for instance in instance_list:
            if relation_field not in related_objects_for_fetch:
                related_objects_for_fetch[relation_field] = []
            related_objects_for_fetch[relation_field].append(
                self._field_to_db(
                    instance._meta.fields_map[related_field_name],
                    getattr(instance, related_field_name),
                    instance,
                )
            )

        related_query.resolve_ordering(
            related_query.model, related_query.model._meta.basetable, [], {}
        )
        related_object_list = await related_query.filter(
            **{f"{k}__in": v for k, v in related_objects_for_fetch.items()}
        )

        related_object_map: Dict[str, list] = {}
        for entry in related_object_list:
            object_id = getattr(entry, relation_field)
            if object_id in related_object_map.keys():
                related_object_map[object_id].append(entry)
            else:
                related_object_map[object_id] = [entry]
        for instance in instance_list:
            relation_container = getattr(instance, field)
            relation_container._set_result_for_query(
                related_object_map.get(getattr(instance, related_field_name), []),
                to_attr,
            )
        return instance_list

    async def _prefetch_reverse_o2o_relation(
        self,
        instance_list: "Iterable[Model]",
        field: str,
        related_query: Tuple[Optional[str], "QuerySet"],
    ) -> "Iterable[Model]":
        to_attr, related_query = related_query
        related_objects_for_fetch: Dict[str, list] = {}
        related_field: BackwardOneToOneRelation = self.model._meta.fields_map[field]  # type: ignore
        related_field_name = related_field.to_field_instance.model_field_name
        relation_field = related_field.relation_field

        for instance in instance_list:
            if relation_field not in related_objects_for_fetch:
                related_objects_for_fetch[relation_field] = []
            related_objects_for_fetch[relation_field].append(
                self._field_to_db(
                    instance._meta.fields_map[related_field_name],
                    getattr(instance, related_field_name),
                    instance,
                )
            )

        related_object_list = await related_query.filter(
            **{f"{k}__in": v for k, v in related_objects_for_fetch.items()}
        )

        related_object_map = {}
        for entry in related_object_list:
            object_id = getattr(entry, relation_field)
            related_object_map[object_id] = entry

        for instance in instance_list:
            obj = related_object_map.get(getattr(instance, related_field_name), None)
            setattr(
                instance,
                f"_{field}",
                obj,
            )
            if to_attr:
                setattr(instance, to_attr, obj)
        return instance_list

    async def _prefetch_m2m_relation(
        self,
        instance_list: "Iterable[Model]",
        field: str,
        related_query: Tuple[Optional[str], "QuerySet"],
    ) -> "Iterable[Model]":
        to_attr, related_query = related_query
        instance_id_set: set = {
            self._field_to_db(instance._meta.pk, instance.pk, instance)
            for instance in instance_list
        }

        field_object: ManyToManyFieldInstance = self.model._meta.fields_map[field]  # type: ignore

        through_table = Table(field_object.through)

        subquery = (
            self.db.query_class.from_(through_table)
            .select(
                through_table[field_object.backward_key].as_("_backward_relation_key"),
                through_table[field_object.forward_key].as_("_forward_relation_key"),
            )
            .where(through_table[field_object.backward_key].isin(instance_id_set))
        )

        related_query_table = related_query.model._meta.basetable
        related_pk_field = related_query.model._meta.db_pk_column
        related_query.resolve_ordering(related_query.model, related_query_table, [], {})
        query = (
            related_query.query.join(subquery)
            .on(subquery._forward_relation_key == related_query_table[related_pk_field])
            .select(
                subquery._backward_relation_key.as_("_backward_relation_key"),
                *[related_query_table[field].as_(field) for field in related_query.fields],
            )
        )

        if related_query._q_objects:
            joined_tables: List[Table] = []
            modifier = QueryModifier()
            for node in related_query._q_objects:
                node._annotations = related_query._annotations
                node._custom_filters = related_query._custom_filters
                modifier &= node.resolve(
                    model=related_query.model,
                    table=related_query_table,
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

        _, raw_results = await self.db.execute_query(query.get_sql())
        # TODO: we should only resolve the PK's once
        relations = [
            (
                self.model._meta.pk.to_python_value(e["_backward_relation_key"]),
                field_object.related_model._meta.pk.to_python_value(e[related_pk_field]),
            )
            for e in raw_results
        ]
        related_object_list = [related_query.model._init_from_db(**e) for e in raw_results]
        await self.__class__(
            model=related_query.model, db=self.db, prefetch_map=related_query._prefetch_map
        )._execute_prefetch_queries(related_object_list)
        related_object_map = {e.pk: e for e in related_object_list}
        relation_map: Dict[str, list] = {}

        for object_id, related_object_id in relations:
            if object_id not in relation_map:
                relation_map[object_id] = []
            relation_map[object_id].append(related_object_map[related_object_id])

        for instance in instance_list:
            relation_container = getattr(instance, field)
            relation_container._set_result_for_query(relation_map.get(instance.pk, []), to_attr)
        return instance_list

    async def _prefetch_direct_relation(
        self,
        instance_list: "Iterable[Model]",
        field: str,
        related_query: Tuple[Optional[str], "QuerySet"],
    ) -> "Iterable[Model]":
        # TODO: This will only work if instance_list is all of same type
        # TODO: If that's the case, then we can optimize the key resolver
        to_attr, related_query = related_query
        related_objects_for_fetch: Dict[str, list] = {}
        relation_key_field = f"{field}_id"
        for instance in instance_list:
            if getattr(instance, relation_key_field):
                key = cast(RelationalField, instance._meta.fields_map[field]).to_field
                if key not in related_objects_for_fetch:
                    related_objects_for_fetch[key] = []
                related_objects_for_fetch[key].append(getattr(instance, relation_key_field))
            else:
                setattr(instance, field, None)

        if related_objects_for_fetch:
            related_object_list = await related_query.filter(
                **{f"{k}__in": v for k, v in related_objects_for_fetch.items()}
            )
            related_object_map = {getattr(obj, key): obj for obj in related_object_list}
            for instance in instance_list:
                obj = related_object_map.get(getattr(instance, relation_key_field))
                setattr(instance, field, obj)
                if to_attr:
                    setattr(instance, to_attr, obj)
        return instance_list

    def _make_prefetch_queries(self) -> None:
        for field_name, forwarded_prefetches in self.prefetch_map.items():
            to_attr = None
            if field_name in self._prefetch_queries:
                to_attr, related_query = self._prefetch_queries[field_name][0]
            else:
                relation_field = self.model._meta.fields_map[field_name]
                related_model: "Type[Model]" = relation_field.related_model  # type: ignore
                related_query = related_model.all().using_db(self.db)
                related_query.query = copy(related_query.model._meta.basequery)
            if forwarded_prefetches:
                related_query = related_query.prefetch_related(*forwarded_prefetches)
            self._prefetch_queries.setdefault(field_name, []).append((to_attr, related_query))

    async def _do_prefetch(
        self,
        instance_id_list: "Iterable[Model]",
        field: str,
        related_query: Tuple[Optional[str], "QuerySet"],
    ) -> "Iterable[Model]":
        if field in self.model._meta.backward_fk_fields:
            return await self._prefetch_reverse_relation(instance_id_list, field, related_query)

        if field in self.model._meta.backward_o2o_fields:
            return await self._prefetch_reverse_o2o_relation(instance_id_list, field, related_query)

        if field in self.model._meta.m2m_fields:
            return await self._prefetch_m2m_relation(instance_id_list, field, related_query)
        return await self._prefetch_direct_relation(instance_id_list, field, related_query)

    async def _execute_prefetch_queries(
        self, instance_list: "Iterable[Model]"
    ) -> "Iterable[Model]":
        if instance_list and (self.prefetch_map or self._prefetch_queries):
            self._make_prefetch_queries()
            prefetch_tasks = []
            for field, related_queries in self._prefetch_queries.items():
                for related_query in related_queries:
                    prefetch_tasks.append(self._do_prefetch(instance_list, field, related_query))
            await asyncio.gather(*prefetch_tasks)

        return instance_list

    async def fetch_for_list(
        self, instance_list: "Iterable[Model]", *args: str
    ) -> "Iterable[Model]":
        self.prefetch_map = {}
        for relation in args:
            first_level_field, __, forwarded_prefetch = relation.partition("__")
            if first_level_field not in self.model._meta.fetch_fields:
                raise OperationalError(
                    f"relation {first_level_field} for {self.model._meta.db_table} not found"
                )

            if first_level_field not in self.prefetch_map.keys():
                self.prefetch_map[first_level_field] = set()

            if forwarded_prefetch:
                self.prefetch_map[first_level_field].add(forwarded_prefetch)

        await self._execute_prefetch_queries(instance_list)
        return instance_list

    @classmethod
    def get_overridden_filter_func(cls, filter_func: Callable) -> Optional[Callable]:
        return cls.FILTER_FUNC_OVERRIDE.get(filter_func)
