from __future__ import annotations

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


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


def init_apps(*models: type[Model]) -> None:
    apps = StateApps()
    for model in models:
        apps.register_model("models", model)
    apps._init_relations()


@pytest.mark.asyncio
async def test_create_model_generates_table_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    await editor.create_model(Widget)

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert 'CREATE TABLE "widget"' in sql
    assert '"id" INT' in sql
    assert "PRIMARY KEY" in sql


@pytest.mark.asyncio
async def test_add_field_generates_add_column_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    await editor.add_field(Widget, "name")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert 'ALTER TABLE "widget" ADD COLUMN' in sql
    assert '"name" TEXT' in sql


@pytest.mark.asyncio
async def test_remove_field_generates_drop_column_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    await editor.remove_field(Widget, Widget._meta.fields_map["name"])

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" DROP COLUMN "name" CASCADE'


@pytest.mark.asyncio
async def test_add_field_m2m_generates_table_sql() -> None:
    class Tag(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()

        class Meta:
            table = "tag"
            app = "models"

    class WidgetWithTags(Model):
        id = fields.IntField(pk=True)
        tags = fields.ManyToManyField("models.Tag", related_name="widgets")

        class Meta:
            table = "widget"
            app = "models"

    init_apps(Tag, WidgetWithTags)

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    await editor.add_field(WidgetWithTags, "tags")

    assert client.executed
    assert 'CREATE TABLE "widget_tag"' in client.executed[0]
