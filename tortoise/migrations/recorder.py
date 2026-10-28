from __future__ import annotations

from datetime import datetime, timezone

from pypika_tortoise import Table

from tortoise import fields
from tortoise.migrations.graph import MigrationKey
from tortoise.models import Model


class MigrationRecorder:
    def __init__(self, connection, *, table_name: str = "tortoise_migrations") -> None:
        self.connection = connection
        self.table_name = table_name
        self.model = self._make_model(table_name)

    def _make_model(self, table_name: str) -> type[Model]:
        class MigrationRecord(Model):
            id = fields.IntField(primary_key=True)
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
        if schema_editor.DIALECT == "mssql":
            statement = (
                f"IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{self.table_name}')\n"  # nosec B608
                f"BEGIN\n{statement}\nEND"
            )
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
        table = Table(self.table_name)
        query = (
            self.connection.query_class.from_(table)
            .select(table.app, table.name)
            .orderby(table.applied_at)
            .orderby(table.app)
            .orderby(table.name)
        )
        try:
            _, rows = await self.connection.execute_query(*query.get_parameterized_sql())
        except Exception:
            return []
        return [MigrationKey(app_label=row["app"], name=row["name"]) for row in rows]

    async def record_applied(self, app: str, name: str) -> None:
        query = (
            self.connection.query_class.into(Table(self.table_name))
            .columns("app", "name", "applied_at")
            .insert(app, name, datetime.now(timezone.utc))
        )
        await self.connection.execute_insert(*query.get_parameterized_sql())

    async def record_unapplied(self, app: str, name: str) -> None:
        table = Table(self.table_name)
        query = (
            self.connection.query_class.from_(table)
            .where(table.app == app)
            .where(table.name == name)
            .delete()
        )
        await self.connection.execute_query(*query.get_parameterized_sql())
