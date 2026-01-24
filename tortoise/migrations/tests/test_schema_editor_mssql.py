import pytest

from tortoise import fields
from tortoise.backends.base.client import Capabilities
from tortoise.migrations.schema_editor.mssql import MSSQLSchemaEditor
from tortoise.models import Model


class FakeClient:
    def __init__(self) -> None:
        self.capabilities = Capabilities("mssql")
        self.executed: list[str] = []

    async def execute_script(self, query: str) -> None:
        self.executed.append(query)


class Widget(Model):
    id = fields.IntField(pk=True)
    slug = fields.CharField(max_length=64, unique=True)

    class Meta:
        table = "widget"
        app = "models"


@pytest.mark.asyncio
async def test_mssql_remove_field_drops_dependencies() -> None:
    client = FakeClient()
    editor = MSSQLSchemaEditor(client)

    await editor.remove_field(Widget, Widget._meta.fields_map["slug"])

    assert client.executed
    cleanup_sql = client.executed[0]
    assert "sys.key_constraints" in cleanup_sql
    assert "sys.indexes" in cleanup_sql
    assert "sys.default_constraints" in cleanup_sql
    assert "DROP COLUMN [slug]" in client.executed[-1]
