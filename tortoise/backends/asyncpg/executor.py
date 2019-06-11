from typing import List, Optional

import asyncpg
from pypika import Parameter, Table

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor


class AsyncpgExecutor(BaseExecutor):
    EXPLAIN_PREFIX = "EXPLAIN (FORMAT JSON, VERBOSE)"

    def _prepare_insert_statement(self, columns: List[str]) -> str:
        query = (
            self.db.query_class.into(Table(self.model._meta.table))
            .columns(*columns)
            .insert(*[Parameter("$%d" % (i + 1,)) for i in range(len(columns))])
        )
        generated_fields = self.model._meta.generated_db_fields
        if generated_fields:
            query = query.returning(*generated_fields)
        return str(query)

    async def _process_insert_result(self, instance: Model, results: Optional[asyncpg.Record]):
        if results:
            generated_fields = self.model._meta.generated_db_fields
            for key, val in zip(generated_fields, results):
                setattr(instance, key, val)
