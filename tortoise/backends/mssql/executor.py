from typing import Any

from tortoise.backends.odbc.executor import ODBCExecutor
from tortoise.exceptions import UnSupportedError


class MSSQLExecutor(ODBCExecutor):
    async def execute_explain(self, sql: str) -> Any:
        raise UnSupportedError("MSSQL does not support explain")
