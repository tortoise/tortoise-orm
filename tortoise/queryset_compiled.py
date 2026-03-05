from __future__ import annotations as _

import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, TypeVar, cast

from pypika_tortoise.queries import QueryBuilder, Table

from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned
from tortoise.parameter import CollectionParameter, Parameter, TortoiseSqlContext
from tortoise.query_utils import Prefetch
from tortoise.queryset import (
    MODEL,
    AwaitableQuery,
    FieldSelectQuery,
    QuerySet,
    ValuesListQuery,
    ValuesQuery,
)

if sys.version_info >= (3, 11):  # pragma: nocoverage
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from tortoise import Model


T = TypeVar("T")


class CachedSql:
    __slots__ = (
        "sql",
        "params",
        "param_by_name",
        "need_params",
        "need_collection_params",
    )

    def __init__(self, sql: str, params: list[Parameter | Any]) -> None:
        self.sql = sql
        self.params = params
        self.param_by_name: dict[str, Parameter] = {}
        self.need_params: dict[str, int] = {}
        self.need_collection_params: dict[str, list[int]] = defaultdict(list)
        for idx, param in enumerate(params):
            if not isinstance(param, Parameter):
                continue

            if param.name not in self.param_by_name:
                self.param_by_name[param.name] = param

            if isinstance(param, CollectionParameter):
                self.need_collection_params[param.name].append(idx)
            else:
                self.need_params[param.name] = idx

    def make_filled_params(self, params: dict[str, Any]) -> list[Any]:
        # TODO: check for parameters mismatch

        filled_params = self.params.copy()
        for name, idx in self.need_params.items():
            param = self.param_by_name[name]
            filled_params[idx] = param.encode_value(params[name])

        for name, indexes in self.need_collection_params.items():
            param = cast(CollectionParameter, self.param_by_name[name])
            collection = param.encode_collection(params[name])
            if len(collection) != len(indexes):
                raise ValueError(
                    f"Provided value length ({len(collection)}) "
                    f"for parameter {name!r} does not match "
                    f"parameter indexes length ({len(indexes)})"
                )
            for idx, value in zip(indexes, collection):
                filled_params[idx] = param.encode_value(value)

        return filled_params


class BaseCompiledQuery(AwaitableQuery[MODEL], ABC):
    __slots__ = ("_sql_cache", "_dynamic_params", "_dynamic_params_names", "_dynamic_params_init")

    def __init__(self, model: type[MODEL], query: QueryBuilder) -> None:
        super().__init__(model)
        self.query = query
        # TODO: use lru
        self._sql_cache: dict[str, CachedSql] = {}
        self._dynamic_params: dict[str, CollectionParameter] = {}
        self._dynamic_params_names: list[str] = []
        self._dynamic_params_init: bool = False

    def _clone(self) -> Self:
        query = self.__class__.__new__(self.__class__)
        query.model = self.model
        query.query = self.query
        query._capabilities = self._capabilities
        query._annotations = self._annotations

        query._sql_cache = self._sql_cache
        query._dynamic_params = self._dynamic_params
        query._dynamic_params_names = self._dynamic_params_names

        return query

    @abstractmethod
    async def execute(self, **params) -> Any: ...

    def init_params_table(self) -> None:
        _, params = self.query.get_parameterized_sql()
        self._sql_cache = {}
        self._dynamic_params = {
            param.name: param for param in params if isinstance(param, CollectionParameter)
        }
        self._dynamic_params_names = sorted(self._dynamic_params.keys())
        self._dynamic_params_init = True

    def _get_or_create_cached_sql(self, params: dict[str, Any]) -> CachedSql:
        if not self._dynamic_params_init:
            self.init_params_table()

        reset_params = []

        cache_key = f"{self._db.capabilities.dialect}-query"
        for name in self._dynamic_params_names:
            value = params[name]
            if not isinstance(value, (tuple, list, set)):
                # TODO: raise exception?
                continue

            param = self._dynamic_params[name]
            cache_key += f"-{name}{len(value)}"
            param.collection_size = len(value)
            reset_params.append(param)

        # TODO: add ability to limit cache, use lru?
        if cache_key not in self._sql_cache:
            # TODO: probably could be done in a better way?
            ctx = TortoiseSqlContext.copy(
                self.query.QUERY_CLS.SQL_CONTEXT,
                dynamic_params=self._dynamic_params,
            )
            sql, params_ = self.query.get_parameterized_sql(ctx)
            self._sql_cache[cache_key] = CachedSql(sql, params_)

        for param in reset_params:
            param.collection_size = None

        return self._sql_cache[cache_key]

    def sql(self, params_inline=False, **params) -> str:
        old_db = self._db
        self._choose_db_if_not_chosen(False)
        cached_query = self._get_or_create_cached_sql(params)
        self._db = old_db
        return cached_query.sql


# TODO: type single queries
class CompiledQuerySet(BaseCompiledQuery[MODEL]):
    __slots__ = (
        "_prefetch_map",
        "_prefetch_queries",
        "_select_related_idx",
        "_single",
        "_raise_does_not_exist",
        "_select_for_update",
        "_custom_fields",
    )

    def __init__(
        self,
        model: type[MODEL],
        query: QueryBuilder,
        prefetch_map: dict[str, set[str | Prefetch]],
        prefetch_queries: dict[str, list[tuple[str | None, QuerySet]]],
        select_related_idx: list[
            tuple[type[Model], int, Table | str, type[Model], Iterable[str | None]]
        ],
        single: bool,
        raise_does_not_exist: bool,
        select_for_update: bool,
        custom_fields: list[str] | None,
    ) -> None:
        super().__init__(model, query)
        self._prefetch_map = prefetch_map
        self._prefetch_queries = prefetch_queries
        self._select_related_idx = select_related_idx
        self._single = single
        self._raise_does_not_exist = raise_does_not_exist
        self._select_for_update = select_for_update
        self._custom_fields: list[str] | None = custom_fields

    def _clone(self) -> Self:
        queryset = super()._clone()
        queryset._prefetch_map = self._prefetch_map
        queryset._prefetch_queries = self._prefetch_queries
        queryset._select_related_idx = self._select_related_idx
        queryset._single = self._single
        queryset._raise_does_not_exist = self._raise_does_not_exist
        queryset._select_for_update = self._select_for_update
        queryset._custom_fields = self._custom_fields
        return queryset

    async def execute(self, **params) -> list[MODEL]:
        self._choose_db_if_not_chosen(self._select_for_update)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        instance_list = await self._db.executor_class(
            model=self.model,
            db=self._db,
            prefetch_map=self._prefetch_map,
            prefetch_queries=self._prefetch_queries,
            select_related_idx=self._select_related_idx,  # type: ignore
        ).execute_select(
            cached_query.sql,
            filled_params,
            custom_fields=self._custom_fields,
        )
        if self._single:
            if len(instance_list) == 1:
                return instance_list[0]
            if not instance_list:
                if self._raise_does_not_exist:
                    raise DoesNotExist(self.model)
                return None  # type: ignore
            raise MultipleObjectsReturned(self.model)
        return instance_list


class CompiledUpdateQuery(BaseCompiledQuery[MODEL]):
    async def execute(self, **params) -> int:
        self._choose_db_if_not_chosen(True)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        return (await self._db.execute_query(cached_query.sql, filled_params))[0]


class CompiledDeleteQuery(BaseCompiledQuery[MODEL]):
    async def execute(self, **params) -> int:
        self._choose_db_if_not_chosen(True)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        return (await self._db.execute_query(cached_query.sql, filled_params))[0]


class CompiledExistsQuery(BaseCompiledQuery[MODEL]):
    async def execute(self, **params) -> int:
        self._choose_db_if_not_chosen(False)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        result, _ = await self._db.execute_query(cached_query.sql, filled_params)
        return bool(result)


class CompiledCountQuery(BaseCompiledQuery[MODEL]):
    __slots__ = (
        "_limit",
        "_offset",
    )

    def __init__(
        self,
        model: type[MODEL],
        query: QueryBuilder,
        limit: int | None,
        offset: int | None,
    ) -> None:
        super().__init__(model, query)
        self._limit = limit or 0
        self._offset = offset or 0

    def _clone(self) -> Self:
        query = super()._clone()
        query._limit = self._limit
        query._offset = self._offset
        return query

    async def execute(self, **params) -> int:
        self._choose_db_if_not_chosen(False)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        _, result = await self._db.execute_query(cached_query.sql, filled_params)
        if not result:
            return 0
        count = list(dict(result[0]).values())[0] - self._offset
        if self._limit and count > self._limit:
            return self._limit
        return count


# TODO: type single query
class CompiledValuesListQuery(BaseCompiledQuery[MODEL]):
    __slots__ = (
        "fields",
        "_single",
        "_raise_does_not_exist",
        "_flat",
        "_annotations",
    )

    def __init__(
        self,
        model: type[MODEL],
        query: QueryBuilder,
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select_list: tuple[str, ...] | list[str],
        flat: bool,
        annotations: dict[str, Any],
    ) -> None:
        super().__init__(model, query)

        fields_for_select = {str(i): field for i, field in enumerate(fields_for_select_list)}
        self.fields = fields_for_select
        self._single = single
        self._raise_does_not_exist = raise_does_not_exist
        self._flat = flat
        self._annotations = annotations

    def _clone(self) -> Self:
        query = super()._clone()
        query.fields = self.fields
        query._single = self._single
        query._raise_does_not_exist = self._raise_does_not_exist
        query._flat = self._flat
        query._annotations = self._annotations
        return query

    def resolve_to_python_value(self, model: type[MODEL], field: str) -> Callable:
        return FieldSelectQuery.resolve_to_python_value(self, model, field)

    async def execute(self, **params) -> list[Any] | tuple:
        self._choose_db_if_not_chosen(False)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        _, result = await self._db.execute_query(cached_query.sql, filled_params)
        return ValuesListQuery._process_results(self, result)


# TODO: type single query
class CompiledValuesQuery(BaseCompiledQuery[MODEL]):
    __slots__ = (
        "_single",
        "_raise_does_not_exist",
        "_fields_for_select",
        "_annotations",
    )

    def __init__(
        self,
        model: type[MODEL],
        query: QueryBuilder,
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select: dict[str, str],
        annotations: dict[str, Any],
    ) -> None:
        super().__init__(model, query)

        self._single = single
        self._raise_does_not_exist = raise_does_not_exist
        self._fields_for_select = fields_for_select
        self._annotations = annotations

    def _clone(self) -> Self:
        query = super()._clone()
        query._single = self._single
        query._raise_does_not_exist = self._raise_does_not_exist
        query._fields_for_select = self._fields_for_select
        query._annotations = self._annotations
        return query

    def resolve_to_python_value(self, model: type[MODEL], field: str) -> Callable:
        return FieldSelectQuery.resolve_to_python_value(self, model, field)

    async def execute(self, **params) -> list[dict] | dict:
        self._choose_db_if_not_chosen(False)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        result = await self._db.execute_query_dict(cached_query.sql, filled_params)
        return ValuesQuery._process_results(self, result)
