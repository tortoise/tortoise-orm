from tortoise import Model
from tortoise.backends.odbc.executor import ODBCExecutor


class OracleExecutor(ODBCExecutor):
    async def _process_insert_result(self, instance: Model, results: int) -> None:
        sql = "SELECT sequence_name FROM ALL_TAB_IDENTITY_COLS where TABLE_NAME = ? and OWNER = ?"
        ret = await self.db.execute_query_dict(
            sql, values=[instance._meta.db_table, self.db.database]  # type: ignore
        )
        seq = ret[0]["sequence_name"]
        sql = f"SELECT {seq}.CURRVAL FROM DUAL"
        ret = await self.db.execute_query_dict(sql)
        await super(OracleExecutor, self)._process_insert_result(instance, ret[0]["currval"])
