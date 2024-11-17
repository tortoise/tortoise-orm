from __future__ import annotations

from typing import Optional

from pypika import Parameter, Parameterizer

from tortoise import Model
from tortoise.backends.base_postgres.executor import BasePostgresExecutor


class PsycopgExecutor(BasePostgresExecutor):
    async def _process_insert_result(
        self, instance: Model, results: Optional[dict | tuple]
    ) -> None:
        if results:
            db_projection = instance._meta.fields_db_projection_reverse

            if isinstance(results, dict):
                for key, val in results.items():
                    setattr(instance, db_projection[key], val)
            else:
                generated_fields = self.model._meta.generated_db_fields

                for key, val in zip(generated_fields, results):
                    setattr(instance, db_projection[key], val)

    def parameter(self, pos: int) -> Parameter:
        return Parameter("%s")

    @classmethod
    def parameterizer(cls) -> Parameterizer:
        return Parameterizer(placeholder_factory=lambda _: "%s")
