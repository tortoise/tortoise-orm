import uuid
from typing import Any, List, Optional

import asyncpg
from pypika import Parameter
from pypika.terms import Term, ValueWrapper

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.filters import is_in, not_in


def postgres_is_in(field: Term, value: Any) -> Term:
    if value:
        return field.isin(value)
    return ValueWrapper(False)


def post_gres_not_in(field: Term, value: Any) -> Term:
    if value:
        return field.notin(value) | field.isnull()
    return ValueWrapper(True)


class AsyncpgExecutor(BaseExecutor):
    FILTER_FUNC_OVERRIDE = {
        is_in: postgres_is_in,
        not_in: post_gres_not_in,
    }
    EXPLAIN_PREFIX = "EXPLAIN (FORMAT JSON, VERBOSE)"
    DB_NATIVE = BaseExecutor.DB_NATIVE | {bool, uuid.UUID}

    def Parameter(self, pos: int) -> Parameter:
        return Parameter("$%d" % (pos + 1,))

    def _prepare_insert_statement(self, columns: List[str], no_generated: bool = False) -> str:
        query = (
            self.db.query_class.into(self.model._meta.basetable)
            .columns(*columns)
            .insert(*[self.Parameter(i) for i in range(len(columns))])
        )
        if not no_generated:
            generated_fields = self.model._meta.generated_db_fields
            if generated_fields:
                query = query.returning(*generated_fields)
        return str(query)

    async def _process_insert_result(
        self, instance: Model, results: Optional[asyncpg.Record]
    ) -> None:
        if results:
            generated_fields = self.model._meta.generated_db_fields
            db_projection = instance._meta.fields_db_projection_reverse
            for key, val in zip(generated_fields, results):
                setattr(instance, db_projection[key], val)
