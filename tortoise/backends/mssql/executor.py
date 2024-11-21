from typing import Any, Optional, Type, Union

from tortoise import Model, fields
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
    TO_DB_OVERRIDE = {
        fields.BooleanField: to_db_bool,
    }

    async def execute_explain(self, sql: str) -> Any:
        raise UnSupportedError("MSSQL does not support explain")
