from __future__ import annotations as _

import functools
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import Any, Concatenate, Literal, NoReturn, ParamSpec, Protocol, Self, TypeVar, cast

from pypika_tortoise.terms import Term

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned, ParamsError
from tortoise.expressions import Expression, Q
from tortoise.filters import FilterInfoDict
from tortoise.parameter import CollectionParameter, Parameter, TortoiseSqlContext
from tortoise.query_utils import Prefetch
from tortoise.queryset import (
    MODEL,
    SINGLE,
    AwaitableQuery,
    BulkCreateQuery,
    BulkUpdateQuery,
    CountQuery,
    DeleteQuery,
    ExistsQuery,
    QuerySet,
    QuerySetSingle,
    T_co,
    UpdateQuery,
    ValuesListQuery,
    ValuesQuery,
)


class PreparedQuerySetSingle(QuerySetSingle[T_co], Protocol):
    def prepared(self) -> PreparedQuerySet[MODEL]: ...

    async def execute(self, **params) -> list[MODEL]: ...


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


class _PreparedQueryMixin(AwaitableQuery, ABC):
    _cache_key: str
    _prepared: bool
    _sql_cache: dict[str, CachedSql] | None
    _dynamic_params: dict[str, CollectionParameter] | None
    _dynamic_params_names: list[str] | None
    _db_for_write: bool

    __slots__ = ()

    @abstractmethod
    def _clone(self) -> Self: ...

    def prepared(self) -> Self:
        if self._cache_key is None:
            raise ValueError("QuerySet.prepare_sql() must be called before QuerySet.prepared()")

        if self._cache_key in self.model._meta.query_cache:
            return self.model._meta.query_cache[self._cache_key]

        queryset = self._clone()

        queryset._choose_db_if_not_chosen(self._db_for_write)
        queryset._make_query()

        queryset._sql_cache = {}
        _, params = queryset.query.get_parameterized_sql()
        queryset._dynamic_params = {
            param.name: param for param in params if isinstance(param, CollectionParameter)
        }
        queryset._dynamic_params_names = sorted(queryset._dynamic_params.keys())

        queryset._prepared = True

        self.model._meta.query_cache[self._cache_key] = queryset

        return queryset

    def _get_or_create_cached_sql(self, params: dict[str, Any]) -> CachedSql:
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
                self.query.QUERY_CLS.SQL_CONTEXT, dynamic_params=self._dynamic_params
            )
            sql, params_ = self.query.get_parameterized_sql(ctx)
            self._sql_cache[cache_key] = CachedSql(sql, params_)

        for param in reset_params:
            param.collection_size = None

        return self._sql_cache[cache_key]

    @abstractmethod
    async def execute(self, **params) -> Any: ...


P = ParamSpec("P")
T = TypeVar("T")


def _disallow_queryset_methods_on_prepared_query(
    func: Callable[Concatenate[PreparedQuerySet, P], T],
) -> Callable[Concatenate[PreparedQuerySet, P], T]:
    @functools.wraps(func)
    def decorated(self: PreparedQuerySet, *args: P.args, **kwargs: P.kwargs) -> T:
        if self._prepared:
            raise ValueError(f'Cannot call "{func.__name__}" on already prepared queryset.')
        return func(self, *args, **kwargs)

    return decorated


class PreparedQuerySet(QuerySet[MODEL], _PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_prepared",
        "_custom_fields",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(self, model: type[MODEL], cache_key: str) -> None:
        super().__init__(model)
        self._cache_key: str = cache_key
        self._prepared: bool = False
        self._sql_cache: dict[str, CachedSql] | None = None
        self._dynamic_params: dict[str, CollectionParameter] | None = None
        self._dynamic_params_names: list[str] | None = None
        self._db_for_write = self._select_for_update
        self._custom_fields: list[str] | None = None

    def _clone(self, _new_cls: type[QuerySet[MODEL]] | None = None) -> PreparedQuerySet[MODEL]:
        queryset = cast(Self, super()._clone(_new_cls))
        queryset._cache_key = self._cache_key
        queryset._prepared = self._prepared
        queryset._sql_cache = self._sql_cache
        queryset._dynamic_params = self._dynamic_params
        queryset._dynamic_params_names = self._dynamic_params_names
        queryset._db_for_write = self._db_for_write
        return cast(PreparedQuerySet, queryset)

    def prepare_sql(self, key: str) -> NoReturn:
        raise NotImplementedError("QuerySets must only be prepared once")

    def prepared(self) -> PreparedQuerySet[MODEL]:
        queryset = cast(Self, super().prepared())
        queryset._custom_fields = list(self._annotations.keys())
        return queryset

    async def execute(self, **params) -> list[MODEL]:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        instance_list = await self._db.executor_class(
            model=self.model,
            db=self._db,
            prefetch_map=self._prefetch_map,
            prefetch_queries=self._prefetch_queries,
            select_related_idx=self._select_related_idx,
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

    @_disallow_queryset_methods_on_prepared_query
    def filter(self, *args: Q, **kwargs: Any) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().filter(*args, **kwargs))

    @_disallow_queryset_methods_on_prepared_query
    def exclude(self, *args: Q, **kwargs: Any) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().exclude(*args, **kwargs))

    @_disallow_queryset_methods_on_prepared_query
    def order_by(self, *orderings: str) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().order_by(*orderings))

    @_disallow_queryset_methods_on_prepared_query
    def latest(self, *orderings: str) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().latest(*orderings))

    @_disallow_queryset_methods_on_prepared_query
    def earliest(self, *orderings: str) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().earliest(*orderings))

    @staticmethod
    def _validate_limit(value: int) -> int:
        if value < 0:
            raise ParamsError("Limit should be non-negative number")
        return value

    @_disallow_queryset_methods_on_prepared_query
    def limit(self, limit: int | Parameter) -> PreparedQuerySet[MODEL]:
        if isinstance(limit, int) and limit < 0:
            raise ParamsError("Limit should be non-negative number")
        elif isinstance(limit, Parameter):
            limit.encode = self._validate_limit

        queryset = self._clone()
        queryset._limit = limit  # type: ignore
        return queryset

    @staticmethod
    def _validate_offset(value: int) -> int:
        if value < 0:
            raise ParamsError("Offset should be non-negative number")
        return value

    @_disallow_queryset_methods_on_prepared_query
    def offset(self, offset: int | Parameter) -> PreparedQuerySet[MODEL]:
        if isinstance(offset, int) and offset < 0:
            raise ParamsError("Offset should be non-negative number")
        elif isinstance(offset, Parameter):
            offset.encode = self._validate_offset

        queryset = self._clone()
        queryset._offset = offset  # type: ignore
        if self.capabilities.requires_limit and queryset._limit is None:
            queryset._limit = 1000000
        return queryset

    @_disallow_queryset_methods_on_prepared_query
    def __getitem__(self, key: slice) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().__getitem__(key))

    @_disallow_queryset_methods_on_prepared_query
    def distinct(self) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().distinct())

    @_disallow_queryset_methods_on_prepared_query
    def select_for_update(
        self,
        nowait: bool = False,
        skip_locked: bool = False,
        of: tuple[str, ...] = (),
        no_key: bool = False,
    ) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().select_for_update(nowait, skip_locked, of, no_key))

    @_disallow_queryset_methods_on_prepared_query
    def annotate(self, **kwargs: Expression | Term) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().annotate(**kwargs))

    @_disallow_queryset_methods_on_prepared_query
    def group_by(self, *fields: str) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().group_by(*fields))

    @_disallow_queryset_methods_on_prepared_query
    def values_list(
        self, *fields_: str, flat: bool = False
    ) -> PreparedValuesListQuery[Literal[False]]:
        fields_for_select_list = self._get_fields_list_for_select(*fields_)

        return PreparedValuesListQuery(
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            flat=flat,
            fields_for_select_list=fields_for_select_list,
            distinct=self._distinct,
            limit=self._limit,
            offset=self._offset,
            orderings=self._orderings,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            group_bys=self._group_bys,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
            cache_key=self._cache_key,
        )

    @_disallow_queryset_methods_on_prepared_query
    def values(self, *args: str, **kwargs: str) -> PreparedValuesQuery[Literal[False]]:
        fields_for_select = self._get_fields_for_select(*args, **kwargs)

        return PreparedValuesQuery(
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            fields_for_select=fields_for_select,
            distinct=self._distinct,
            limit=self._limit,
            offset=self._offset,
            orderings=self._orderings,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            group_bys=self._group_bys,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
            cache_key=self._cache_key,
        )

    @_disallow_queryset_methods_on_prepared_query
    def delete(self) -> DeleteQuery:
        return PreparedDeleteQuery(
            model=self.model,
            db=self._db,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
            cache_key=self._cache_key,
        )

    @_disallow_queryset_methods_on_prepared_query
    def update(self, **kwargs: Any) -> PreparedUpdateQuery:
        return PreparedUpdateQuery(
            model=self.model,
            update_kwargs=kwargs,
            db=self._db,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
            cache_key=self._cache_key,
        )

    @_disallow_queryset_methods_on_prepared_query
    def count(self) -> PreparedCountQuery:
        return PreparedCountQuery(
            model=self.model,
            db=self._db,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            offset=self._offset,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
            cache_key=self._cache_key,
        )

    @_disallow_queryset_methods_on_prepared_query
    def exists(self) -> PreparedExistsQuery:
        return PreparedExistsQuery(
            model=self.model,
            db=self._db,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
            cache_key=self._cache_key,
        )

    @_disallow_queryset_methods_on_prepared_query
    def all(self) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().all())

    @_disallow_queryset_methods_on_prepared_query
    def first(self) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().first())

    @_disallow_queryset_methods_on_prepared_query
    def last(self) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().last())

    @_disallow_queryset_methods_on_prepared_query
    def get(self, *args: Q, **kwargs: Any) -> PreparedQuerySetSingle[MODEL]:
        return cast(PreparedQuerySetSingle, super().get(*args, **kwargs))

    async def in_bulk(self, id_list: Iterable[str | int], field_name: str) -> dict[str, MODEL]:
        raise NotImplementedError("Prepared queries don't support in_bulk.")

    def bulk_create(
        self,
        objects: Iterable[MODEL],
        batch_size: int | None = None,
        ignore_conflicts: bool = False,
        update_fields: Iterable[str] | None = None,
        on_conflict: Iterable[str] | None = None,
    ) -> BulkCreateQuery[MODEL]:
        raise NotImplementedError("Prepared queries don't support bulk_create.")

    def bulk_update(
        self,
        objects: Iterable[MODEL],
        fields: Iterable[str],
        batch_size: int | None = None,
    ) -> BulkUpdateQuery[MODEL]:
        raise NotImplementedError("Prepared queries don't support bulk_update.")

    @_disallow_queryset_methods_on_prepared_query
    def get_or_none(self, *args: Q, **kwargs: Any) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().get_or_none(*args, **kwargs))

    @_disallow_queryset_methods_on_prepared_query
    def only(self, *fields_for_select: str) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().only(*fields_for_select))

    @_disallow_queryset_methods_on_prepared_query
    def select_related(self, *fields: str) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().select_related(*fields))

    @_disallow_queryset_methods_on_prepared_query
    def force_index(self, *index_names: str) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().force_index(*index_names))

    @_disallow_queryset_methods_on_prepared_query
    def use_index(self, *index_names: str) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().use_index(*index_names))

    @_disallow_queryset_methods_on_prepared_query
    def prefetch_related(self, *args: str | Prefetch) -> PreparedQuerySet[MODEL]:
        return cast(PreparedQuerySet, super().prefetch_related(*args))


class PreparedUpdateQuery(UpdateQuery, _PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_prepared",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        update_kwargs: dict[str, Any],
        db: BaseDBAsyncClient,
        q_objects: list[Q],
        annotations: dict[str, Any],
        custom_filters: dict[str, FilterInfoDict],
        limit: int | None,
        orderings: list[tuple[str, str]],
        cache_key: str,
    ) -> None:
        super().__init__(
            model,
            update_kwargs,
            db,
            q_objects,
            annotations,
            custom_filters,
            limit,
            orderings,
        )

        self._cache_key: str = cache_key
        self._prepared: bool = False
        self._sql_cache: dict[str, CachedSql] | None = None
        self._dynamic_params: dict[str, CollectionParameter] | None = None
        self._dynamic_params_names: list[str] | None = None
        self._db_for_write: bool = True

    def _clone(self) -> PreparedUpdateQuery:
        query = self.__class__(
            model=self.model,
            update_kwargs=self.update_kwargs,
            db=self._db,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
            cache_key=self._cache_key,
        )
        query._prepared = self._prepared
        return query

    async def execute(self, **params) -> int:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        return (await self._db.execute_query(cached_query.sql, filled_params))[0]


class PreparedDeleteQuery(DeleteQuery, _PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_prepared",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: list[Q],
        annotations: dict[str, Any],
        custom_filters: dict[str, FilterInfoDict],
        limit: int | None,
        orderings: list[tuple[str, str]],
        cache_key: str,
    ) -> None:
        super().__init__(
            model,
            db,
            q_objects,
            annotations,
            custom_filters,
            limit,
            orderings,
        )
        self._cache_key: str = cache_key
        self._prepared: bool = False
        self._sql_cache: dict[str, CachedSql] | None = None
        self._dynamic_params: dict[str, CollectionParameter] | None = None
        self._dynamic_params_names: list[str] | None = None
        self._db_for_write: bool = True

    def _clone(self) -> PreparedDeleteQuery:
        query = self.__class__(
            model=self.model,
            db=self._db,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
            cache_key=self._cache_key,
        )
        query._prepared = self._prepared
        return query

    async def execute(self, **params) -> int:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        return (await self._db.execute_query(cached_query.sql, filled_params))[0]


class PreparedExistsQuery(ExistsQuery, _PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_prepared",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: list[Q],
        annotations: dict[str, Any],
        custom_filters: dict[str, FilterInfoDict],
        force_indexes: set[str],
        use_indexes: set[str],
        cache_key: str,
    ) -> None:
        super().__init__(
            model,
            db,
            q_objects,
            annotations,
            custom_filters,
            force_indexes,
            use_indexes,
        )
        self._cache_key: str = cache_key
        self._prepared: bool = False
        self._sql_cache: dict[str, CachedSql] | None = None
        self._dynamic_params: dict[str, CollectionParameter] | None = None
        self._dynamic_params_names: list[str] | None = None
        self._db_for_write: bool = False

    def _clone(self) -> PreparedExistsQuery:
        query = self.__class__(
            model=self.model,
            db=self._db,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
            cache_key=self._cache_key,
        )
        query._prepared = self._prepared
        return query

    async def execute(self, **params) -> int:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        result, _ = await self._db.execute_query(cached_query.sql, filled_params)
        return bool(result)


class PreparedCountQuery(CountQuery, _PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_prepared",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: list[Q],
        annotations: dict[str, Any],
        custom_filters: dict[str, FilterInfoDict],
        limit: int | None,
        offset: int | None,
        force_indexes: set[str],
        use_indexes: set[str],
        cache_key: str,
    ) -> None:
        super().__init__(
            model,
            db,
            q_objects,
            annotations,
            custom_filters,
            limit,
            offset,
            force_indexes,
            use_indexes,
        )
        self._cache_key: str = cache_key
        self._prepared: bool = False
        self._sql_cache: dict[str, CachedSql] | None = None
        self._dynamic_params: dict[str, CollectionParameter] | None = None
        self._dynamic_params_names: list[str] | None = None
        self._db_for_write: bool = False

    def _clone(self) -> PreparedCountQuery:
        query = self.__class__(
            model=self.model,
            db=self._db,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            offset=self._offset,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
            cache_key=self._cache_key,
        )
        query._prepared = self._prepared
        return query

    async def execute(self, **params) -> int:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        _, result = await self._db.execute_query(cached_query.sql, filled_params)
        if not result:
            return 0
        count = list(dict(result[0]).values())[0] - self._offset
        if self._limit and count > self._limit:
            return self._limit
        return count


class PreparedValuesListQuery(ValuesListQuery[SINGLE], _PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_prepared",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: list[Q],
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select_list: tuple[str, ...] | list[str],
        limit: int | None,
        offset: int | None,
        distinct: bool,
        orderings: list[tuple[str, str]],
        flat: bool,
        annotations: dict[str, Any],
        custom_filters: dict[str, FilterInfoDict],
        group_bys: tuple[str, ...],
        force_indexes: set[str],
        use_indexes: set[str],
        cache_key: str,
    ) -> None:
        super().__init__(
            model,
            db,
            q_objects,
            single,
            raise_does_not_exist,
            fields_for_select_list,
            limit,
            offset,
            distinct,
            orderings,
            flat,
            annotations,
            custom_filters,
            group_bys,
            force_indexes,
            use_indexes,
        )
        self._cache_key: str = cache_key
        self._prepared: bool = False
        self._sql_cache: dict[str, CachedSql] | None = None
        self._dynamic_params: dict[str, CollectionParameter] | None = None
        self._dynamic_params_names: list[str] | None = None
        self._db_for_write: bool = False

    def _clone(self) -> PreparedValuesListQuery:
        query = self.__class__(
            model=self.model,
            db=self._db,
            q_objects=self._q_objects,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            fields_for_select_list=self._fields_for_select_list,
            limit=self._limit,
            offset=self._offset,
            distinct=self._distinct,
            orderings=self._orderings,
            flat=self._flat,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            group_bys=self._group_bys,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
            cache_key=self._cache_key,
        )
        query._prepared = self._prepared
        return query

    async def execute(self, **params) -> list[Any] | tuple:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        _, result = await self._db.execute_query(cached_query.sql, filled_params)
        return self._process_results(result)


class PreparedValuesQuery(ValuesQuery[SINGLE], _PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_prepared",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: list[Q],
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select: dict[str, str],
        limit: int | None,
        offset: int | None,
        distinct: bool,
        orderings: list[tuple[str, str]],
        annotations: dict[str, Any],
        custom_filters: dict[str, FilterInfoDict],
        group_bys: tuple[str, ...],
        force_indexes: set[str],
        use_indexes: set[str],
        cache_key: str,
    ) -> None:
        super().__init__(
            model,
            db,
            q_objects,
            single,
            raise_does_not_exist,
            fields_for_select,
            limit,
            offset,
            distinct,
            orderings,
            annotations,
            custom_filters,
            group_bys,
            force_indexes,
            use_indexes,
        )
        self._cache_key: str = cache_key
        self._prepared: bool = False
        self._sql_cache: dict[str, CachedSql] | None = None
        self._dynamic_params: dict[str, CollectionParameter] | None = None
        self._dynamic_params_names: list[str] | None = None
        self._db_for_write: bool = False

    def _clone(self) -> PreparedValuesQuery:
        query = self.__class__(
            model=self.model,
            db=self._db,
            q_objects=self._q_objects,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            fields_for_select=self._fields_for_select,
            limit=self._limit,
            offset=self._offset,
            distinct=self._distinct,
            orderings=self._orderings,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            group_bys=self._group_bys,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
            cache_key=self._cache_key,
        )
        query._prepared = self._prepared
        return query

    async def execute(self, **params) -> list[dict] | dict:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        result = await self._db.execute_query_dict(cached_query.sql, filled_params)
        return self._process_results(result)
