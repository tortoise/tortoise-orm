from __future__ import annotations

from typing import cast

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.contrib.postgres.fields import TSVectorField
from tortoise.contrib.postgres.indexes import GinIndex
from tortoise.indexes import Index
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
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


@pytest.mark.asyncio
async def test_create_model_generates_generated_column_sql() -> None:
    class SearchDocument(Model):
        id = fields.IntField(pk=True)
        title = fields.TextField()
        body = fields.TextField(null=True)
        search_vector = TSVectorField(
            source_fields=("title", "body"),
            config="english",
            weights=("A", "B"),
        )

        class Meta:
            table = "search_document"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    await editor.create_model(SearchDocument)

    assert client.executed
    sql = client.executed[0]
    assert 'CREATE TABLE "search_document"' in sql
    assert (
        "\"search_vector\" TSVECTOR GENERATED ALWAYS AS (SETWEIGHT(TO_TSVECTOR('english',"
        "COALESCE(\"title\", '')),'A') || SETWEIGHT(TO_TSVECTOR('english',"
        "COALESCE(\"body\", '')),'B')) STORED"
    ) in sql


@pytest.mark.asyncio
async def test_add_field_generates_generated_column_sql() -> None:
    class SearchDocument(Model):
        id = fields.IntField(pk=True)
        title = fields.TextField()
        body = fields.TextField(null=True)
        search_vector = TSVectorField(
            source_fields=("title", "body"),
            config="english",
            weights=("A", "B"),
        )

        class Meta:
            table = "search_document"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    await editor.add_field(SearchDocument, "search_vector")

    assert client.executed
    sql = client.executed[0]
    assert 'ALTER TABLE "search_document" ADD COLUMN' in sql
    assert (
        "\"search_vector\" TSVECTOR GENERATED ALWAYS AS (SETWEIGHT(TO_TSVECTOR('english',"
        "COALESCE(\"title\", '')),'A') || SETWEIGHT(TO_TSVECTOR('english',"
        "COALESCE(\"body\", '')),'B')) STORED"
    ) in sql


@pytest.mark.asyncio
async def test_add_index_generates_gin_tsvector_sql() -> None:
    class SearchDocument(Model):
        id = fields.IntField(pk=True)
        search_vector = TSVectorField()

        class Meta:
            table = "search_document"
            app = "models"
            indexes = [GinIndex(fields=("search_vector",))]

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    index = cast(Index, SearchDocument._meta.indexes[0])
    await editor.add_index(SearchDocument, index)

    assert client.executed
    expected_name = editor._generate_index_name("idx", SearchDocument, ["search_vector"])
    assert (
        f'CREATE INDEX "{expected_name}" ON "search_document" USING GIN ("search_vector");'
    ) == client.executed[0]


@pytest.mark.asyncio
async def test_alter_generated_field_raises() -> None:
    class OldSearchDocument(Model):
        id = fields.IntField(pk=True)
        title = fields.TextField()
        body = fields.TextField(null=True)
        search_vector = TSVectorField(
            source_fields=("title",),
            config="english",
        )

        class Meta:
            table = "search_document"
            app = "models"

    class NewSearchDocument(Model):
        id = fields.IntField(pk=True)
        title = fields.TextField()
        body = fields.TextField(null=True)
        search_vector = TSVectorField(
            source_fields=("title", "body"),
            config="english",
        )

        class Meta:
            table = "search_document"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    with pytest.raises(ValueError):
        await editor.alter_field(OldSearchDocument, NewSearchDocument, "search_vector")
    assert not client.executed


@pytest.mark.asyncio
async def test_create_model_includes_db_default() -> None:
    """CreateModel should include DEFAULT clause for fields with db_default."""

    class WidgetWithDefault(Model):
        id = fields.IntField(pk=True)
        status = fields.CharField(max_length=20, db_default="active")

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    await editor.create_model(WidgetWithDefault)

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert 'CREATE TABLE "widget"' in sql
    assert "DEFAULT 'active'" in sql
