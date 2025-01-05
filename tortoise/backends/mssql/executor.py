from typing import Any, Optional, Type, Union

from tortoise import Model
from tortoise.backends.odbc.executor import ODBCExecutor
from tortoise.exceptions import UnSupportedError
from tortoise.fields import BooleanField


def to_db_bool(
    self: BooleanField, value: Optional[Union[bool, int]], instance: Union[Type[Model], Model]
) -> Optional[int]:
    self.validate(value)
    if value is None:
        return None
    return int(bool(value))


class MSSQLExecutor(ODBCExecutor):
    async def execute_explain(self, sql: str) -> Any:
        raise UnSupportedError("MSSQL does not support explain")
