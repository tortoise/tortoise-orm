import pytest

from tortoise import fields
from tortoise.backends.base.client import Capabilities
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.schema_editor.sqlite import SqliteSchemaEditor
from tortoise.models import Model


class FakeClient:
    def __init__(self) -> None:
        self.capabilities = Capabilities("sqlite")
        self.executed: list[str] = []

    async def execute_script(self, query: str) -> None:
        self.executed.append(query)


class Widget(Model):
    id = fields.IntField(pk=True)
    slug = fields.CharField(max_length=50, unique=True)

    class Meta:
        table = "widget"
        app = "models"


@pytest.mark.asyncio
async def test_sqlite_add_field_unique_uses_index() -> None:
    client = FakeClient()
    editor = SqliteSchemaEditor(client)

    await editor.add_field(Widget, "slug")

    assert len(client.executed) == 2
    add_column_sql = client.executed[0]
    unique_index_sql = client.executed[1]
    assert 'ALTER TABLE "widget" ADD COLUMN' in add_column_sql
    assert "UNIQUE" not in add_column_sql
    assert "CREATE UNIQUE INDEX" in unique_index_sql
    assert '"slug"' in unique_index_sql


@pytest.mark.asyncio
async def test_sqlite_constraint_name_used_for_drop() -> None:
    client = FakeClient()
    editor = SqliteSchemaEditor(client)

    constraint = UniqueConstraint(fields=("slug",))
    constraint_name = editor._constraint_name_for_model(Widget, constraint)

    await editor.add_constraint(Widget, constraint)
    await editor.remove_constraint(Widget, constraint)

    assert constraint_name in client.executed[0]
    assert f'DROP INDEX "{constraint_name}"' in client.executed[1]
