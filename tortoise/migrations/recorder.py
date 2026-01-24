from __future__ import annotations

from datetime import datetime, timezone

from tortoise import fields
from tortoise.models import Model
from tortoise.migrations.graph import MigrationKey


class MigrationRecorder:
    def __init__(self, connection, *, table_name: str = "tortoise_migrations") -> None:
        self.connection = connection
        self.table_name = table_name
        self.model = self._make_model(table_name)

    def _make_model(self, table_name: str) -> type[Model]:
        class MigrationRecord(Model):
            id = fields.IntField(pk=True)
            app = fields.CharField(max_length=255)
            name = fields.CharField(max_length=255)
            applied_at = fields.DatetimeField()

            class Meta:
                table = table_name
                app = "_migrations"
                unique_together = (("app", "name"),)

        return MigrationRecord

    async def ensure_schema(self, schema_editor) -> None:
        sql_data = schema_editor._get_model_sql_data(self.model)
        statement = sql_data.table_sql
        if schema_editor.DIALECT in {"sqlite", "postgres", "mysql"}:
            statement = statement.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)
            await schema_editor.client.execute_script(statement)
            return
        try:
            await schema_editor.client.execute_script(statement)
        except Exception as exc:  # pragma: nocoverage - best effort for non-IF-NOT-EXISTS backends
            message = str(exc).lower()
            if "already exists" in message or "ora-00955" in message:
                return
            raise

    async def applied_migrations(self) -> list[MigrationKey]:
        query = (
            f'SELECT "app", "name" FROM "{self.table_name}" '
            'ORDER BY "app", "name"'
        )
        try:
            _, rows = await self.connection.execute_query(query)
        except Exception:
            return []
        return [MigrationKey(app_label=row["app"], name=row["name"]) for row in rows]

    async def record_applied(self, app: str, name: str) -> None:
        applied_at = datetime.now(timezone.utc).isoformat()
        query = (
            f'INSERT INTO "{self.table_name}" ("app", "name", "applied_at") '
            f"VALUES ('{self._escape(app)}', '{self._escape(name)}', '{applied_at}')"
        )
        await self.connection.execute_script(query)

    async def record_unapplied(self, app: str, name: str) -> None:
        query = (
            f'DELETE FROM "{self.table_name}" '
            f"WHERE \"app\" = '{self._escape(app)}' AND \"name\" = '{self._escape(name)}'"
        )
        await self.connection.execute_script(query)

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("'", "''")
