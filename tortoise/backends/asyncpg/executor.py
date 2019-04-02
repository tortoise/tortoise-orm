from typing import List

from pypika import Parameter, Table

from tortoise.backends.base.executor import BaseExecutor


class AsyncpgExecutor(BaseExecutor):

    EXPLAIN_PREFIX = "EXPLAIN (FORMAT JSON, VERBOSE)"

    def _prepare_insert_statement(self, columns: List[str]) -> str:
        return str(
            self.db.query_class.into(Table(self.model._meta.table))
            .columns(*columns)
            .insert(*[Parameter("$%d" % (i + 1,)) for i in range(len(columns))])
            .returning("id")
        )
