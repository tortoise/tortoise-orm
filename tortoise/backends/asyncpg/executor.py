from typing import List

from pypika import Table

from tortoise.backends.base.executor import BaseExecutor


class AsyncpgExecutor(BaseExecutor):
    def _prepare_insert_statement(self, columns: List[str]) -> str:
        return str(
            self.connection.query_class.into(Table(self.model._meta.table)).columns(*columns)
            .insert('???').returning('id')
        ).replace("'???'", ','.join(['$%d' % (i + 1, ) for i in range(len(columns))]))
