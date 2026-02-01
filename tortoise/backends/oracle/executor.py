from __future__ import annotations

from typing import TYPE_CHECKING, cast

from tortoise import Model
from tortoise.backends.odbc.executor import ODBCExecutor

if TYPE_CHECKING:
    from .client import OracleClient  # pylint: disable=W0611


class OracleExecutor(ODBCExecutor):
    async def _process_insert_result(self, instance: Model, results: int) -> None:
        sql = "SELECT SEQUENCE_NAME FROM ALL_TAB_IDENTITY_COLS where TABLE_NAME = ? and OWNER = ?"
        db = cast("OracleClient", self.db)
        ret = await db.execute_query_dict(sql, values=[instance._meta.db_table, db.database])
        try:
            seq = ret[0]["SEQUENCE_NAME"]
        except IndexError:
            return
        sql = f"SELECT {seq}.CURRVAL FROM DUAL"  # nosec:B608
        ret = await db.execute_query_dict(sql)
        await super()._process_insert_result(instance, ret[0]["CURRVAL"])
