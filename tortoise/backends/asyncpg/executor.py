import uuid
from typing import List, Optional

import asyncpg
from pypika import Parameter

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor


class AsyncpgExecutor(BaseExecutor):
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
