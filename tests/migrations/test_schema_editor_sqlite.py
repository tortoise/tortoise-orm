from __future__ import annotations

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.schema_editor.sqlite import SqliteSchemaEditor
from tortoise.models import Model


class Widget(Model):
    id = fields.IntField(pk=True)
    slug = fields.CharField(max_length=50, unique=True)

    class Meta:
        table = "widget"
        app = "models"


@pytest.mark.asyncio
async def test_sqlite_add_field_unique_uses_index() -> None:
    client = FakeClient("sqlite")
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
    client = FakeClient("sqlite")
    editor = SqliteSchemaEditor(client)

    constraint = UniqueConstraint(fields=("slug",))
    constraint_name = editor._constraint_name_for_model(Widget, constraint)

    await editor.add_constraint(Widget, constraint)
    await editor.remove_constraint(Widget, constraint)

    assert constraint_name in client.executed[0]
    assert f'DROP INDEX "{constraint_name}"' in client.executed[1]
