import pytest

from tortoise import fields
from tortoise.backends.base.client import Capabilities
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.models import Model


class FakeClient:
    def __init__(self) -> None:
        self.capabilities = Capabilities("sql")
        self.executed: list[str] = []

    async def execute_script(self, query: str) -> None:
        self.executed.append(query)


class TestSchemaEditor(BaseSchemaEditor):
    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return ""

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return ""


class Widget(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    class Meta:
        table = "widget"
        app = "models"


@pytest.mark.asyncio
async def test_create_model_generates_table_sql() -> None:
    client = FakeClient()
    editor = TestSchemaEditor(client)

    await editor.create_model(Widget)

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert 'CREATE TABLE "widget"' in sql
    assert '"id" INT' in sql
    assert "PRIMARY KEY" in sql


@pytest.mark.asyncio
async def test_add_field_generates_add_column_sql() -> None:
    client = FakeClient()
    editor = TestSchemaEditor(client)

    await editor.add_field(Widget, "name")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert 'ALTER TABLE "widget" ADD COLUMN' in sql
    assert '"name" TEXT' in sql


@pytest.mark.asyncio
async def test_remove_field_generates_drop_column_sql() -> None:
    client = FakeClient()
    editor = TestSchemaEditor(client)

    await editor.remove_field(Widget, Widget._meta.fields_map["name"])

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" DROP COLUMN "name" CASCADE'
