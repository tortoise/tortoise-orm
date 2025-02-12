import uuid
from collections.abc import Sequence
from typing import Optional, cast

from pypika_tortoise.dialects import PostgreSQLQueryBuilder
from pypika_tortoise.terms import Term

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.contrib.postgres.array_functions import (
    postgres_array_contained_by,
    postgres_array_contains,
    postgres_array_length,
    postgres_array_overlap,
)
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


def postgres_search(field: Term, value: Term) -> SearchCriterion:
    return SearchCriterion(field, expr=value)


class BasePostgresExecutor(BaseExecutor):
    EXPLAIN_PREFIX = "EXPLAIN (FORMAT JSON, VERBOSE)"
    DB_NATIVE = BaseExecutor.DB_NATIVE | {bool, uuid.UUID}
    FILTER_FUNC_OVERRIDE = {
        search: postgres_search,
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

    async def _process_insert_result(self, instance: Model, results: Optional[dict]) -> None:
        if results:
            generated_fields = self.model._meta.generated_db_fields
            db_projection = instance._meta.fields_db_projection_reverse
            for key, val in zip(generated_fields, results):
                setattr(instance, db_projection[key], val)
