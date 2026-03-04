from __future__ import annotations as _

import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Literal, NoReturn, Protocol, TypeVar, cast

from pypika_tortoise.queries import QueryBuilder, Table
from pypika_tortoise.terms import Term

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned, ParamsError
from tortoise.expressions import Expression, Q
from tortoise.parameter import CollectionParameter, Parameter, TortoiseSqlContext
from tortoise.query_utils import Prefetch
from tortoise.queryset import (
    MODEL,
    PRIMARY_KEY,
    SINGLE,
    AwaitableQuery,
    BulkCreateQuery,
    BulkUpdateQuery,
    DeleteQuery,
    QuerySet,
    QuerySetSingle,
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


class PreparedQuerySetSingle(QuerySetSingle[T], Protocol[T]):
    def prefetch_related(
        self, *args: str | Prefetch
    ) -> PreparedQuerySetSingle[T]: ...  # pragma: nocoverage

    def select_related(self, *args: str) -> PreparedQuerySetSingle[T]: ...  # pragma: nocoverage

    def annotate(
        self, **kwargs: Expression | Term
    ) -> PreparedQuerySetSingle[T]: ...  # pragma: nocoverage

    def only(self, *fields_for_select: str) -> PreparedQuerySetSingle[T]: ...  # pragma: nocoverage

    def values_list(
        self, *fields_: str, flat: bool = False
    ) -> PreparedValuesListQuery[Literal[True]]: ...  # pragma: nocoverage

    def values(
        self, *args: str, **kwargs: str
    ) -> PreparedValuesQuery[Literal[True]]: ...  # pragma: nocoverage

    def prepared(self) -> PreparedQuerySetSingle[T]: ...

    async def execute(self, **params) -> T: ...


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


class _PreparedQueryMixin(AwaitableQuery[MODEL], ABC):
    _cache_key: str
    _sql_cache: dict[str, CachedSql]
    _dynamic_params: dict[str, CollectionParameter]
    _dynamic_params_names: list[str]
    _db_for_write: bool

    @abstractmethod
    def _clone(self) -> Self: ...

    def prepare_sql(self, key: str) -> NoReturn:
        raise NotImplementedError("QuerySets must be prepared only once")

    def prepared(self) -> Self:
        return self

    def _init_prepared(self) -> None:
        _, params = self.query.get_parameterized_sql()
        self._sql_cache = {}
        self._dynamic_params = {
            param.name: param for param in params if isinstance(param, CollectionParameter)
        }
        self._dynamic_params_names = sorted(self._dynamic_params.keys())
        self.model._meta.query_cache[self._cache_key] = self

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
                self.query.QUERY_CLS.SQL_CONTEXT,
                dynamic_params=self._dynamic_params,
            )
            sql, params_ = self.query.get_parameterized_sql(ctx)
            self._sql_cache[cache_key] = CachedSql(sql, params_)

        for param in reset_params:
            param.collection_size = None

        return self._sql_cache[cache_key]

    @abstractmethod
    async def execute(self, **params) -> Any: ...

    def sql(self, params_inline=False, **params) -> str:
        cached_query = self._get_or_create_cached_sql(params)
        return cached_query.sql

    def filter(self, *args: Q, **kwargs: Any) -> Self:
        return self

    def exclude(self, *args: Q, **kwargs: Any) -> Self:
        return self

    def order_by(self, *orderings: str) -> Self:
        return self

    def latest(self, *orderings: str) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, self)

    def earliest(self, *orderings: str) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, self)

    def limit(self, limit: int | Parameter) -> Self:
        return self

    def offset(self, offset: int | Parameter) -> Self:
        return self

    def __getitem__(self, key: slice) -> Self:
        return self

    def distinct(self) -> Self:
        return self

    def select_for_update(
        self,
        nowait: bool = False,
        skip_locked: bool = False,
        of: tuple[str, ...] = (),
        no_key: bool = False,
    ) -> Self:
        return self

    def annotate(self, **kwargs: Expression | Term) -> Self:
        return self

    def group_by(self, *fields: str) -> Self:
        return self

    def values_list(
        self, *fields_: str, flat: bool = False
    ) -> PreparedValuesListQuery[Literal[False]]:
        return cast(PreparedValuesListQuery, self)

    def values(self, *args: str, **kwargs: str) -> PreparedValuesQuery[Literal[False]]:
        return cast(PreparedValuesQuery, self)

    def delete(self) -> DeleteQuery:
        return cast(DeleteQuery, self)

    def update(self, **kwargs: Any) -> PreparedUpdateQuery:
        return cast(PreparedUpdateQuery, self)

    def count(self) -> PreparedCountQuery:
        return cast(PreparedCountQuery, self)

    def exists(self) -> PreparedExistsQuery:
        return cast(PreparedExistsQuery, self)

    def all(self) -> Self:
        return self

    def first(self) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, self)

    def last(self) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, self)

    def get(self, *args: Q, **kwargs: Any) -> PreparedQuerySetSingle[MODEL]:
        return cast(PreparedQuerySetSingle, self)

    async def in_bulk(
        self, id_list: Iterable[PRIMARY_KEY], field_name: str
    ) -> dict[PRIMARY_KEY, MODEL]:
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

    def get_or_none(self, *args: Q, **kwargs: Any) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, self)

    def only(self, *fields_for_select: str) -> Self:
        return self

    def select_related(self, *fields: str) -> Self:
        return self

    def force_index(self, *index_names: str) -> Self:
        return self

    def use_index(self, *index_names: str) -> Self:
        return self

    def prefetch_related(self, *args: str | Prefetch) -> Self:
        return self


class PreparingQuerySet(QuerySet[MODEL]):
    __slots__ = ("_cache_key",)

    def __init__(self, model: type[MODEL], cache_key: str) -> None:
        super().__init__(model)
        self._cache_key: str = cache_key

    def _clone(self, _new_cls: type[QuerySet[MODEL]] | None = None) -> PreparingQuerySet[MODEL]:
        queryset = cast(Self, super()._clone(_new_cls))
        queryset._cache_key = self._cache_key
        return cast(PreparingQuerySet, queryset)

    def prepared(self) -> PreparedQuerySet:
        if self._cache_key in self.model._meta.query_cache:
            return cast(PreparedQuerySet, self.model._meta.query_cache[self._cache_key])

        self._db = self._choose_db(self._select_for_update)
        self._make_query()

        prepared = PreparedQuerySet(
            model=self.model,
            db=self._db,
            query=self.query,
            prefetch_map=self._prefetch_map,
            prefetch_queries=self._prefetch_queries,
            select_related_idx=self._select_related_idx,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            select_for_update=self._select_for_update,
            custom_fields=list(self._annotations.keys()),
            cache_key=self._cache_key,
        )
        prepared._init_prepared()
        return prepared

    def prepare_sql(self, key: str) -> NoReturn:
        raise NotImplementedError("QuerySets must be prepared only once")

    def filter(self, *args: Q, **kwargs: Any) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().filter(*args, **kwargs))

    def exclude(self, *args: Q, **kwargs: Any) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().exclude(*args, **kwargs))

    def order_by(self, *orderings: str) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().order_by(*orderings))

    def latest(self, *orderings: str) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().latest(*orderings))

    def earliest(self, *orderings: str) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().earliest(*orderings))

    @staticmethod
    def _validate_limit(value: int) -> int:
        if value < 0:
            raise ParamsError("Limit should be non-negative number")
        return value

    def limit(self, limit: int | Parameter) -> PreparingQuerySet[MODEL]:
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

    def offset(self, offset: int | Parameter) -> PreparingQuerySet[MODEL]:
        if isinstance(offset, int) and offset < 0:
            raise ParamsError("Offset should be non-negative number")
        elif isinstance(offset, Parameter):
            offset.encode = self._validate_offset

        queryset = self._clone()
        queryset._offset = offset  # type: ignore
        if self.capabilities.requires_limit and queryset._limit is None:
            queryset._limit = 1000000
        return queryset

    def __getitem__(self, key: slice) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().__getitem__(key))

    def distinct(self) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().distinct())

    def select_for_update(
        self,
        nowait: bool = False,
        skip_locked: bool = False,
        of: tuple[str, ...] = (),
        no_key: bool = False,
    ) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().select_for_update(nowait, skip_locked, of, no_key))

    def annotate(self, **kwargs: Expression | Term) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().annotate(**kwargs))

    def group_by(self, *fields: str) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().group_by(*fields))

    def values_list(
        self, *fields_: str, flat: bool = False
    ) -> PreparedValuesListQuery[Literal[False]]:
        fields_for_select_list = self._get_fields_list_for_select(*fields_)
        query = super().values_list(*fields_, flat=flat)
        query._db = query._choose_db(True)
        query._make_query()

        prepared: PreparedValuesListQuery = PreparedValuesListQuery(
            db=query._db,
            model=self.model,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            flat=flat,
            fields_for_select_list=fields_for_select_list,
            annotations=self._annotations,
            query=query.query,
            cache_key=self._cache_key,
        )
        prepared._init_prepared()
        return prepared

    def values(self, *args: str, **kwargs: str) -> PreparedValuesQuery[Literal[False]]:
        fields_for_select = self._get_fields_for_select(*args, **kwargs)
        query = super().values(*args, **kwargs)
        query._db = query._choose_db(True)
        query._make_query()

        prepared: PreparedValuesQuery = PreparedValuesQuery(
            db=query._db,
            model=self.model,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            fields_for_select=fields_for_select,
            annotations=self._annotations,
            query=query.query,
            cache_key=self._cache_key,
        )
        prepared._init_prepared()
        return prepared

    def delete(self) -> PreparedDeleteQuery:  # type: ignore
        query = super().delete()
        query._db = query._choose_db(True)
        query._make_query()

        prepared = PreparedDeleteQuery(
            model=self.model,
            db=query._db,
            query=query.query,
            cache_key=self._cache_key,
        )
        prepared._init_prepared()
        return prepared

    def update(self, **kwargs: Any) -> PreparedUpdateQuery:  # type: ignore
        query = super().update(**kwargs)
        query._db = query._choose_db(True)
        query._make_query()

        prepared = PreparedUpdateQuery(
            model=self.model,
            db=query._db,
            query=query.query,
            cache_key=self._cache_key,
        )
        prepared._init_prepared()
        return prepared

    def count(self) -> PreparedCountQuery:  # type: ignore
        query = super().count()
        query._db = query._choose_db(True)
        query._make_query()

        prepared = PreparedCountQuery(
            model=self.model,
            db=query._db,
            query=query.query,
            limit=self._limit,
            offset=self._offset,
            cache_key=self._cache_key,
        )
        prepared._init_prepared()
        return prepared

    def exists(self) -> PreparedExistsQuery:  # type: ignore
        query = super().exists()
        query._db = query._choose_db(True)
        query._make_query()

        prepared = PreparedExistsQuery(
            model=self.model,
            db=query._db,
            query=query.query,
            cache_key=self._cache_key,
        )
        prepared._init_prepared()
        return prepared

    def all(self) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().all())

    def first(self) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().first())

    def last(self) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().last())

    def get(self, *args: Q, **kwargs: Any) -> PreparedQuerySetSingle[MODEL]:
        return cast(PreparedQuerySetSingle, super().get(*args, **kwargs))

    async def in_bulk(
        self, id_list: Iterable[PRIMARY_KEY], field_name: str
    ) -> dict[PRIMARY_KEY, MODEL]:
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

    def get_or_none(self, *args: Q, **kwargs: Any) -> PreparedQuerySetSingle[MODEL | None]:
        return cast(PreparedQuerySetSingle, super().get_or_none(*args, **kwargs))

    def only(self, *fields_for_select: str) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().only(*fields_for_select))

    def select_related(self, *fields: str) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().select_related(*fields))

    def force_index(self, *index_names: str) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().force_index(*index_names))

    def use_index(self, *index_names: str) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().use_index(*index_names))

    def prefetch_related(self, *args: str | Prefetch) -> PreparingQuerySet[MODEL]:
        return cast(PreparingQuerySet, super().prefetch_related(*args))


class PreparedQuerySet(_PreparedQueryMixin[MODEL]):
    __slots__ = (
        "_cache_key",
        "_custom_fields",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        query: QueryBuilder,
        db: BaseDBAsyncClient,
        prefetch_map: dict[str, set[str | Prefetch]],
        prefetch_queries: dict[str, list[tuple[str | None, QuerySet]]],
        select_related_idx: list[
            tuple[type[Model], int, Table | str, type[Model], Iterable[str | None]]
        ],
        single: bool,
        raise_does_not_exist: bool,
        select_for_update: bool,
        custom_fields: list[str] | None,
        cache_key: str,
    ) -> None:
        super().__init__(model)
        self._db = db
        self._prefetch_map = prefetch_map
        self._prefetch_queries = prefetch_queries
        self._select_related_idx = select_related_idx
        self._single = single
        self._raise_does_not_exist = raise_does_not_exist
        self._db_for_write = select_for_update
        self._custom_fields: list[str] | None = custom_fields

        self.query = query
        self._cache_key: str = cache_key
        self._sql_cache: dict[str, CachedSql] = {}
        self._dynamic_params: dict[str, CollectionParameter] = {}
        self._dynamic_params_names: list[str] = []

    def prepared(self) -> PreparedQuerySet[MODEL]:
        return self

    def _clone(self) -> PreparedQuerySet[MODEL]:
        queryset = self.__class__.__new__(self.__class__)
        queryset.model = self.model
        queryset.query = self.query
        queryset._capabilities = self._capabilities
        queryset._annotations = self._annotations

        queryset._db = self._db
        queryset._prefetch_map = self._prefetch_map
        queryset._prefetch_queries = self._prefetch_queries
        queryset._select_related_idx = self._select_related_idx
        queryset._single = self._single
        queryset._raise_does_not_exist = self._raise_does_not_exist
        queryset._db_for_write = self._db_for_write
        queryset._custom_fields = self._custom_fields

        queryset._cache_key = self._cache_key
        queryset._sql_cache = self._sql_cache
        queryset._dynamic_params = self._dynamic_params
        queryset._dynamic_params_names = self._dynamic_params_names
        return queryset

    async def execute(self, **params) -> list[MODEL]:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        self._choose_db_if_not_chosen(self._db_for_write)
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


class PreparedUpdateQuery(_PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        query: QueryBuilder,
        cache_key: str,
    ) -> None:
        super().__init__(model)
        self._db = db
        self.query = query

        self._cache_key: str = cache_key
        self._sql_cache: dict[str, CachedSql] = {}
        self._dynamic_params: dict[str, CollectionParameter] = {}
        self._dynamic_params_names: list[str] = []
        self._db_for_write: bool = True

    def prepared(self) -> PreparedUpdateQuery:
        return self

    def _clone(self) -> PreparedUpdateQuery:
        query = self.__class__.__new__(self.__class__)
        query.model = self.model
        query.query = self.query
        query._db = self._db
        query._capabilities = self._capabilities
        query._annotations = self._annotations

        query._cache_key = self._cache_key
        query._db_for_write = self._db_for_write
        query._sql_cache = self._sql_cache
        query._dynamic_params = self._dynamic_params
        query._dynamic_params_names = self._dynamic_params_names

        return query

    async def execute(self, **params) -> int:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        return (await self._db.execute_query(cached_query.sql, filled_params))[0]


class PreparedDeleteQuery(_PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        query: QueryBuilder,
        cache_key: str,
    ) -> None:
        super().__init__(model)
        self._db = db
        self.query = query

        self._cache_key: str = cache_key
        self._sql_cache: dict[str, CachedSql] = {}
        self._dynamic_params: dict[str, CollectionParameter] = {}
        self._dynamic_params_names: list[str] = []
        self._db_for_write: bool = True

    def prepared(self) -> PreparedDeleteQuery:
        return self

    def _clone(self) -> PreparedDeleteQuery:
        query = self.__class__.__new__(self.__class__)
        query.model = self.model
        query.query = self.query
        query._capabilities = self._capabilities
        query._annotations = self._annotations
        query._db = self._db
        query._cache_key = self._cache_key
        query._db_for_write = self._db_for_write
        query._sql_cache = self._sql_cache
        query._dynamic_params = self._dynamic_params
        query._dynamic_params_names = self._dynamic_params_names

        return query

    async def execute(self, **params) -> int:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        return (await self._db.execute_query(cached_query.sql, filled_params))[0]


class PreparedExistsQuery(_PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        query: QueryBuilder,
        cache_key: str,
    ) -> None:
        super().__init__(model)
        self._db = db
        self.query = query

        self._cache_key: str = cache_key
        self._sql_cache: dict[str, CachedSql] = {}
        self._dynamic_params: dict[str, CollectionParameter] = {}
        self._dynamic_params_names: list[str] = []
        self._db_for_write: bool = False

    def prepared(self) -> PreparedExistsQuery:
        return self

    def _clone(self) -> PreparedExistsQuery:
        query = self.__class__.__new__(self.__class__)
        query.model = self.model
        query.query = self.query
        query._capabilities = self._capabilities
        query._annotations = self._annotations
        query._db = self._db
        query._cache_key = self._cache_key
        query._db_for_write = self._db_for_write
        query._sql_cache = self._sql_cache
        query._dynamic_params = self._dynamic_params
        query._dynamic_params_names = self._dynamic_params_names

        return query

    async def execute(self, **params) -> int:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)
        result, _ = await self._db.execute_query(cached_query.sql, filled_params)
        return bool(result)


class PreparedCountQuery(_PreparedQueryMixin):
    __slots__ = (
        "_limit",
        "_offset",
        "_cache_key",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        query: QueryBuilder,
        limit: int | None,
        offset: int | None,
        cache_key: str,
    ) -> None:
        super().__init__(model)
        self._db = db
        self.query = query
        self._limit = limit or 0
        self._offset = offset or 0

        self._cache_key: str = cache_key
        self._sql_cache: dict[str, CachedSql] = {}
        self._dynamic_params: dict[str, CollectionParameter] = {}
        self._dynamic_params_names: list[str] = []
        self._db_for_write: bool = False

    def prepared(self) -> PreparedCountQuery:
        return self

    def _clone(self) -> PreparedCountQuery:
        query = self.__class__.__new__(self.__class__)
        query.model = self.model
        query.query = self.query
        query._capabilities = self._capabilities
        query._annotations = self._annotations
        query._db = self._db
        query._limit = self._limit
        query._offset = self._offset
        query._cache_key = self._cache_key
        query._db_for_write = self._db_for_write
        query._sql_cache = self._sql_cache
        query._dynamic_params = self._dynamic_params
        query._dynamic_params_names = self._dynamic_params_names

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
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select_list: tuple[str, ...] | list[str],
        flat: bool,
        annotations: dict[str, Any],
        query: QueryBuilder,
        cache_key: str,
    ) -> None:
        super().__init__(
            model=model,
            db=db,
            q_objects=[],
            single=single,
            raise_does_not_exist=raise_does_not_exist,
            fields_for_select_list=fields_for_select_list,
            limit=None,
            offset=None,
            distinct=False,
            orderings=[],
            flat=flat,
            annotations=annotations,
            custom_filters={},
            group_bys=(),
            force_indexes=set(),
            use_indexes=set(),
        )
        self.query = query

        self._cache_key: str = cache_key
        self._sql_cache: dict[str, CachedSql] = {}
        self._dynamic_params: dict[str, CollectionParameter] = {}
        self._dynamic_params_names: list[str] = []
        self._db_for_write: bool = False

    def prepared(self) -> PreparedValuesListQuery[SINGLE]:
        return self

    def _clone(self) -> PreparedValuesListQuery[SINGLE]:
        query = self.__class__.__new__(self.__class__)
        query.model = self.model
        query.query = self.query
        query._db = self._db
        query._capabilities = self._capabilities

        query.fields = self.fields
        query._limit = self._limit
        query._offset = self._offset
        query._distinct = self._distinct
        query._orderings = self._orderings
        query._custom_filters = self._custom_filters
        query._q_objects = self._q_objects
        query._single = self._single
        query._raise_does_not_exist = self._raise_does_not_exist
        query._fields_for_select_list = self._fields_for_select_list
        query._flat = self._flat
        query._group_bys = self._group_bys
        query._force_indexes = self._force_indexes
        query._use_indexes = self._use_indexes
        query._fields_to_select_sql = self._fields_to_select_sql
        query._annotations = self._annotations

        query._cache_key = self._cache_key
        query._db_for_write = self._db_for_write
        query._sql_cache = self._sql_cache
        query._dynamic_params = self._dynamic_params
        query._dynamic_params_names = self._dynamic_params_names

        return query

    async def execute(self, **params) -> list[Any] | tuple:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        _, result = await self._db.execute_query(cached_query.sql, filled_params)
        return self._process_results(result)


class PreparedValuesQuery(ValuesQuery[SINGLE], _PreparedQueryMixin):
    __slots__ = (
        "_cache_key",
        "_sql_cache",
        "_dynamic_params",
        "_dynamic_params_names",
        "_db_for_write",
    )

    def __init__(
        self,
        model: type[MODEL],
        db: BaseDBAsyncClient,
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select: dict[str, str],
        annotations: dict[str, Any],
        query: QueryBuilder,
        cache_key: str,
    ) -> None:
        super().__init__(
            model=model,
            db=db,
            q_objects=[],
            single=single,
            raise_does_not_exist=raise_does_not_exist,
            fields_for_select=fields_for_select,
            limit=None,
            offset=None,
            distinct=False,
            orderings=[],
            annotations=annotations,
            custom_filters={},
            group_bys=(),
            force_indexes=set(),
            use_indexes=set(),
        )

        self.query = query
        self._cache_key: str = cache_key
        self._sql_cache: dict[str, CachedSql] = {}
        self._dynamic_params: dict[str, CollectionParameter] = {}
        self._dynamic_params_names: list[str] = []
        self._db_for_write: bool = False

    def prepared(self) -> PreparedValuesQuery[SINGLE]:
        return self

    def _clone(self) -> PreparedValuesQuery[SINGLE]:
        query = self.__class__.__new__(self.__class__)
        query.model = self.model
        query.query = self.query
        query._db = self._db
        query._capabilities = self._capabilities

        query._fields_for_select = self._fields_for_select
        query._limit = self._limit
        query._offset = self._offset
        query._distinct = self._distinct
        query._orderings = self._orderings
        query._custom_filters = self._custom_filters
        query._q_objects = self._q_objects
        query._single = self._single
        query._raise_does_not_exist = self._raise_does_not_exist
        query._db = self._db
        query._group_bys = self._group_bys
        query._force_indexes = self._force_indexes
        query._use_indexes = self._use_indexes
        query._annotations = self._annotations

        query._cache_key = self._cache_key
        query._db_for_write = self._db_for_write
        query._sql_cache = self._sql_cache
        query._dynamic_params = self._dynamic_params
        query._dynamic_params_names = self._dynamic_params_names

        return query

    async def execute(self, **params) -> list[dict] | dict:
        cached_query = self._get_or_create_cached_sql(params)
        filled_params = cached_query.make_filled_params(params)

        result = await self._db.execute_query_dict(cached_query.sql, filled_params)
        return self._process_results(result)
