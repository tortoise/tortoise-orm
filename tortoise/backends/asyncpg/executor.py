from typing import Optional

import asyncpg

from tortoise import MODEL_INSTANCE
from tortoise.backends.base_postgres.executor import BasePostgresExecutor


class AsyncpgExecutor(BasePostgresExecutor):
    async def _process_insert_result(
        self, instance: MODEL_INSTANCE, results: Optional[asyncpg.Record]
    ) -> None:
        return await super()._process_insert_result(instance, results)
