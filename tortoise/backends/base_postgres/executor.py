from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from functools import partial
from typing import TYPE_CHECKING, cast

from pypika_tortoise.dialects import PostgreSQLQueryBuilder
from pypika_tortoise.queries import QueryBuilder
from pypika_tortoise.terms import Term, ValueWrapper

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.contrib.postgres.array_functions import (
    postgres_array_contained_by,
    postgres_array_contains,
    postgres_array_length,
    postgres_array_overlap,
)
from tortoise.contrib.postgres.functions import PlainToTsQuery
from tortoise.contrib.postgres.json_functions import (
    postgres_json_contained_by,
    postgres_json_contains,
    postgres_json_filter,
)
from tortoise.contrib.postgres.regex import (
    postgres_insensitive_posix_regex,
    postgres_posix_regex,
)
from tortoise.contrib.postgres.search import SearchCriterion
from tortoise.filters import (
    array_contained_by,
    array_contains,
    array_length,
    array_overlap,
    insensitive_posix_regex,
    json_contained_by,
    json_contains,
    json_filter,
    posix_regex,
    search,
)

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.filters import FilterInfoDict


def postgres_search(
    field: Term, value: Term | str, field_is_vector: bool = False
) -> SearchCriterion:
    query = value if isinstance(value, Term) else PlainToTsQuery(ValueWrapper(value))
    return SearchCriterion(field, expr=query, vectorize=not field_is_vector)


class BasePostgresExecutor(BaseExecutor):
    EXPLAIN_PREFIX = "EXPLAIN (FORMAT JSON, VERBOSE)"
    DB_NATIVE = BaseExecutor.DB_NATIVE | {bool, uuid.UUID}
    FILTER_FUNC_OVERRIDE = {
        array_contains: postgres_array_contains,
        array_contained_by: postgres_array_contained_by,
        array_overlap: postgres_array_overlap,
        json_contains: postgres_json_contains,
        json_contained_by: postgres_json_contained_by,
        json_filter: postgres_json_filter,
        posix_regex: postgres_posix_regex,
        insensitive_posix_regex: postgres_insensitive_posix_regex,
        array_length: postgres_array_length,
    }

    @classmethod
    def get_overridden_filter_func(
        cls, filter_func: Callable, filter_info: FilterInfoDict | None = None
    ) -> Callable | None:
        if filter_func is search:
            field_is_vector = bool(filter_info and filter_info.get("is_tsvector"))
            return partial(postgres_search, field_is_vector=field_is_vector)
        return super().get_overridden_filter_func(filter_func, filter_info)

    def _prepare_insert_statement(
        self, columns: Sequence[str], has_generated: bool = True, ignore_conflicts: bool = False
    ) -> PostgreSQLQueryBuilder:
        builder = cast(PostgreSQLQueryBuilder, self.db.query_class.into(self.model._meta.basetable))
        query = builder.columns(*columns).insert(*[self.parameter(i) for i in range(len(columns))])
        if has_generated and (generated_fields := self.model._meta.generated_db_fields):
            query = query.returning(*generated_fields)
        if ignore_conflicts:
            query = query.on_conflict().do_nothing()
        return query

    def _add_returning_to_insert(
        self,
        query: QueryBuilder,
        has_generated: bool,
        db_default_columns: list[str],
    ) -> QueryBuilder:
        returning_fields = self._get_returning_fields(has_generated, db_default_columns)
        if returning_fields:
            query = query.returning(*returning_fields)  # type: ignore[operator]
        return query

    async def _process_insert_result(self, instance: Model, results: dict | None) -> None:
        if results:
            db_projection = instance._meta.fields_db_projection_reverse
            for key, val in results.items():
                if key in db_projection:
                    model_field = db_projection[key]
                    field_object = self.model._meta.fields_map[model_field]
                    setattr(instance, model_field, field_object.to_python_value(val))
