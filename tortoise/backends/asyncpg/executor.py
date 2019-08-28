from typing import List, Optional

import asyncpg
from pypika import Parameter, Table

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor


class AsyncpgExecutor(BaseExecutor):
    EXPLAIN_PREFIX = "EXPLAIN (FORMAT JSON, VERBOSE)"

    def Parameter(self, pos: int) -> Parameter:
        return Parameter("$%d" % (pos + 1,))

    def _prepare_insert_statement(self, columns: List[str]) -> str:
        query = (
            self.db.query_class.into(Table(self.model._meta.table))
            .columns(*columns)
            .insert(*[self.Parameter(i) for i in range(len(columns))])
        )
        generated_fields = self.model._meta.generated_db_fields
        if generated_fields:
            query = query.returning(*generated_fields)
        return str(query)

    async def _process_insert_result(self, instance: Model, results: Optional[asyncpg.Record]):
        if results:
            generated_fields = self.model._meta.generated_db_fields
            db_projection = instance._meta.fields_db_projection_reverse
            for key, val in zip(generated_fields, results):
                setattr(instance, db_projection[key], val)

    async def execute_update(self, instance, update_fields: Optional[List[str]]) -> None:
        # The only difference is Postgres respects the parameter ordering,
        # so we need to put PK at front.
        values = [self.model._meta.pk.to_db_value(instance.pk, instance)]
        if update_fields:
            for field in update_fields:
                field_object = self.model._meta.fields_map[field]
                if not field_object.generated:
                    values.append(self.column_map[field](getattr(instance, field), instance))
        else:
            for field, db_field in self.model._meta.fields_db_projection.items():
                field_object = self.model._meta.fields_map[field]
                if not field_object.generated:
                    values.append(self.column_map[field](getattr(instance, field), instance))

        await self.db.execute_query(self.get_update_sql(update_fields), values)
