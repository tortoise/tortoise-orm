import uuid
from typing import Optional, Sequence

import asyncpg
from pypika import Parameter
from pypika.terms import Term

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.contrib.postgres.json_functions import (
    postgres_json_contained_by,
    postgres_json_contains,
    postgres_json_filter,
)
from tortoise.contrib.postgres.search import SearchCriterion
from tortoise.filters import json_contained_by, json_contains, json_filter, search


def postgres_search(field: Term, value: Term):
    return SearchCriterion(field, expr=value)


class AsyncpgExecutor(BaseExecutor):
    EXPLAIN_PREFIX = "EXPLAIN (FORMAT JSON, VERBOSE)"
    DB_NATIVE = BaseExecutor.DB_NATIVE | {bool, uuid.UUID}
    FILTER_FUNC_OVERRIDE = {
        search: postgres_search,
        json_contains: postgres_json_contains,
        json_contained_by: postgres_json_contained_by,
        json_filter: postgres_json_filter,
    }

    def parameter(self, pos: int) -> Parameter:
        return Parameter("$%d" % (pos + 1,))

    def _prepare_insert_statement(
        self, columns: Sequence[str], has_generated: bool = True, ignore_conflicts: bool = False
    ) -> str:
        query = (
            self.db.query_class.into(self.model._meta.basetable)
            .columns(*columns)
            .insert(*[self.parameter(i) for i in range(len(columns))])
        )
        if has_generated:
            generated_fields = self.model._meta.generated_db_fields
            if generated_fields:
                query = query.returning(*generated_fields)
        if ignore_conflicts:
            query = query.do_nothing()
        return str(query)

    async def _process_insert_result(
        self, instance: Model, results: Optional[asyncpg.Record]
    ) -> None:
        if results:
            generated_fields = self.model._meta.generated_db_fields
            db_projection = instance._meta.fields_db_projection_reverse
            for key, val in zip(generated_fields, results):
                setattr(instance, db_projection[key], val)
