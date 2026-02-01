from __future__ import annotations

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.migrations.schema_editor.mssql import MSSQLSchemaEditor
from tortoise.models import Model


class Widget(Model):
    id = fields.IntField(pk=True)
    slug = fields.CharField(max_length=64, unique=True)

    class Meta:
        table = "widget"
        app = "models"


@pytest.mark.asyncio
async def test_mssql_remove_field_drops_dependencies() -> None:
    client = FakeClient("mssql")
    editor = MSSQLSchemaEditor(client)

    await editor.remove_field(Widget, Widget._meta.fields_map["slug"])

    assert client.executed
    cleanup_sql = client.executed[0]
    assert "sys.key_constraints" in cleanup_sql
    assert "sys.indexes" in cleanup_sql
    assert "sys.default_constraints" in cleanup_sql
    assert "DROP COLUMN [slug]" in client.executed[-1]
