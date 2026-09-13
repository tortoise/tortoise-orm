from __future__ import annotations

from pypika_tortoise import Parameter

from tortoise import Model
from tortoise.backends.base_postgres.executor import BasePostgresExecutor


class PsycopgExecutor(BasePostgresExecutor):
    async def _process_insert_result(self, instance: Model, results: dict | None) -> None:
        if results:
            db_projection = instance._meta.fields_db_projection_reverse
            for key, val in results.items():
                if key in db_projection:
                    model_field = db_projection[key]
                    field_object = self.model._meta.fields_map[model_field]
                    setattr(instance, model_field, field_object.to_python_value(val))

    def parameter(self, pos: int) -> Parameter:
        return Parameter("%s")
