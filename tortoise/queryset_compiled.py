from __future__ import annotations as _

import sys
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, Generic, Literal, Protocol, TypeVar, cast, overload

from pypika_tortoise.queries import QueryBuilder, Table

from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned
from tortoise.parameter import CollectionParameter, Parameter, TortoiseSqlContext
from tortoise.query_utils import Prefetch
from tortoise.queryset import (
    MODEL,
    SINGLE,
    AwaitableQuery,
    FieldSelectQuery,
    QuerySet,
    T_co,
    ValuesListQuery,
    ValuesQuery,
)

if sys.version_info >= (3, 11):  # pragma: nocoverage
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from tortoise import Model


class CompiledQuerySetSingle(Protocol[T_co]):
    def sql(self, **params) -> str: ...

    async def execute(self, **params) -> MODEL: ...


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
        for name in self.need_params:
            if name not in params:
                raise KeyError(f'Expected parameter "{name}" is not provided!')

        for name, indexes in self.need_collection_params.items():
            if name not in params:
                raise KeyError(f'Expected parameter "{name}" is not provided!')
            collection_length = len(params[name])
            param_length = len(params[name])
            if collection_length != param_length:
                raise ValueError(
                    f"Provided value length ({collection_length}) "
                    f"for parameter {name!r} does not match "
                    f"parameter indexes length ({param_length})"
                )

        filled_params = self.params.copy()
        for name, idx in self.need_params.items():
            param = self.param_by_name[name]
            filled_params[idx] = param.encode_value(params[name])

        for name, indexes in self.need_collection_params.items():
            param = cast(CollectionParameter, self.param_by_name[name])
            collection = param.encode_collection(params[name])
            for idx, value in zip(indexes, collection):
                filled_params[idx] = param.encode_value(value)

        return filled_params


class _BoundedLRU(Generic[T]):
    __slots__ = ("_data", "_maxsize")

    def __init__(self, maxsize: int) -> None:
        self._data: OrderedDict[str, T] = OrderedDict()
        self._maxsize = maxsize

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @maxsize.setter
    def maxsize(self, value: int) -> None:
        self._maxsize = value

    def get(self, key: str) -> T | None:
        try:
            self._data.move_to_end(key)
            return self._data[key]
        except KeyError:
            return None

    def put(self, key: str, value: T) -> None:
        if key in self._data:
            self._data.move_to_end(key)
            self._data[key] = value
        else:
            if len(self._data) >= self._maxsize:
                self._data.popitem(last=False)
            self._data[key] = value


class BaseCompiledQuery(AwaitableQuery[MODEL], ABC):
    DEFAULT_CACHE_SIZE_SIMPLE = 2
    DEFAULT_CACHE_SIZE_COLLECTIONS = 128

    __slots__ = (
        "_sql_cache",
        "_collection_params",
        "_collection_params_names",
    )

    def __init__(
        self, model: type[MODEL], query: QueryBuilder, sql_cache_maxsize: int | None
    ) -> None:
        super().__init__(model)
        self.query = query
        self._sql_cache: _BoundedLRU[CachedSql] = _BoundedLRU(0)
        self._collection_params: dict[str, CollectionParameter] = {}
        self._collection_params_names: list[str] = []

        sql, params = self.query.get_parameterized_sql()
        self._collection_params = {
            param.name: param for param in params if isinstance(param, CollectionParameter)
        }
        if self._collection_params:
            self._collection_params_names = sorted(self._collection_params.keys())
            self._sql_cache.maxsize = sql_cache_maxsize or self.DEFAULT_CACHE_SIZE_COLLECTIONS
        else:
            self._sql_cache.maxsize = sql_cache_maxsize or self.DEFAULT_CACHE_SIZE_SIMPLE

    def _clone(self) -> Self:
        query = self.__class__.__new__(self.__class__)
        query.model = self.model
        query.query = self.query
        query._db = None  # type: ignore
        query._capabilities = self._capabilities
        query._annotations = self._annotations

        query._sql_cache = self._sql_cache
        query._collection_params = self._collection_params
        query._collection_params_names = self._collection_params_names

        return query

    @abstractmethod
    async def execute(self, **params) -> Any: ...

    def _get_or_create_cached_sql_simple(self) -> CachedSql:
        cache_key = self._db.capabilities.dialect
        if (cached := self._sql_cache.get(cache_key)) is None:
            cached = CachedSql(*self.query.get_parameterized_sql())
            self._sql_cache.put(cache_key, cached)
        return cached

    def _get_or_create_cached_sql(self, params: dict[str, Any]) -> CachedSql:
        if not self._collection_params:
            return self._get_or_create_cached_sql_simple()

        cache_key = self._db.capabilities.dialect

        reset_params = []

        cache_key_parts = []
        for name in self._collection_params_names:
            value = params[name]
            if not isinstance(value, (tuple, list, set)):
                raise ValueError(f'Expected parameter "{name}" to be a collection, got {value!r}')

            param = self._collection_params[name]
            cache_key_parts.append(f"-{name}:{len(value)}")
            param.collection_size = len(value)
            reset_params.append(param)

        if self._sql_cache.get(cache_key) is None:
            # TODO: probably could be done in a better way?
            ctx = TortoiseSqlContext.copy(
                self.query.QUERY_CLS.SQL_CONTEXT,
                dynamic_params=self._collection_params,
            )
            sql, params_ = self.query.get_parameterized_sql(ctx)
            self._sql_cache.put(cache_key, CachedSql(sql, params_))

        for param in reset_params:
            param.collection_size = None

        return cast(CachedSql, self._sql_cache.get(cache_key))

    def sql(self, params_inline=False, **params) -> str:
        old_db = self._db
        self._choose_db_if_not_chosen(False)
        cached_query = self._get_or_create_cached_sql(params)
        self._db = old_db
        return cached_query.sql


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
        sql_cache_maxsize: int | None,
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
        super().__init__(model, query, sql_cache_maxsize)
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
        sql_cache_maxsize: int | None,
        limit: int | None,
        offset: int | None,
    ) -> None:
        super().__init__(model, query, sql_cache_maxsize)
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


class CompiledValuesListQuery(BaseCompiledQuery[MODEL], Generic[MODEL, SINGLE]):
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
        sql_cache_maxsize: int | None,
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select_list: tuple[str, ...] | list[str],
        flat: bool,
        annotations: dict[str, Any],
    ) -> None:
        super().__init__(model, query, sql_cache_maxsize)

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

    @overload
    async def execute(self: CompiledValuesListQuery[MODEL, Literal[True]], **params) -> tuple: ...

    @overload
    async def execute(
        self: CompiledValuesListQuery[MODEL, Literal[False]], **params
    ) -> list[Any]: ...

    async def execute(self, **params) -> list[Any] | tuple:
        self._choose_db_if_not_chosen(False)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        _, result = await self._db.execute_query(cached_query.sql, filled_params)
        return ValuesListQuery._process_results(self, result)


class CompiledValuesQuery(BaseCompiledQuery[MODEL], Generic[MODEL, SINGLE]):
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
        sql_cache_maxsize: int | None,
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select: dict[str, str],
        annotations: dict[str, Any],
    ) -> None:
        super().__init__(model, query, sql_cache_maxsize)

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

    @overload
    async def execute(self: CompiledValuesQuery[MODEL, Literal[True]], **params) -> dict: ...

    @overload
    async def execute(self: CompiledValuesQuery[MODEL, Literal[False]], **params) -> list[dict]: ...

    async def execute(self, **params) -> list[dict] | dict:
        self._choose_db_if_not_chosen(False)
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        result = await self._db.execute_query_dict(cached_query.sql, filled_params)
        return ValuesQuery._process_results(self, result)
