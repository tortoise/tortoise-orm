from __future__ import annotations

from typing import cast

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.contrib.postgres.fields import TSVectorField
from tortoise.contrib.postgres.indexes import GinIndex
from tortoise.indexes import Index
from tortoise.migrations.constraints import CheckConstraint, UniqueConstraint
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
from tortoise.migrations.schema_editor.mysql import MySQLSchemaEditor
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
        tags = fields.ManyToManyField(Tag, related_name="widgets")

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


@pytest.mark.asyncio
async def test_create_model_includes_db_default_on_fk() -> None:
    """CreateModel should include DEFAULT clause for FK columns with db_default."""

    class Dc(Model):
        id = fields.IntField(primary_key=True)

        class Meta:
            table = "dc"
            app = "models"

    class App(Model):
        id = fields.IntField(primary_key=True)
        dc: fields.ForeignKeyRelation[Dc] = fields.ForeignKeyField("models.Dc", db_default=2)

        class Meta:
            table = "app"
            app = "models"

    init_apps(Dc, App)

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    await editor.create_model(App)

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert 'CREATE TABLE "app"' in sql
    assert '"dc_id"' in sql
    assert "DEFAULT 2" in sql


@pytest.mark.asyncio
async def test_create_model_includes_meta_constraints() -> None:
    """CreateModel must emit named UniqueConstraint and CheckConstraint in CREATE TABLE."""

    class Like(Model):
        id = fields.IntField(pk=True)
        types = fields.CharField(max_length=10)
        user_id = fields.IntField()
        art_id = fields.IntField()
        score = fields.IntField()

        class Meta:
            table = "like"
            app = "models"
            constraints = [
                UniqueConstraint(fields=("types", "user_id", "art_id"), name="unique_like"),
                CheckConstraint(check="score >= 0", name="chk_score_positive"),
            ]

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    await editor.create_model(Like)

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert 'CONSTRAINT "unique_like" UNIQUE ("types", "user_id", "art_id")' in sql
    assert 'CONSTRAINT "chk_score_positive" CHECK (score >= 0)' in sql


@pytest.mark.asyncio
async def test_create_model_skips_unique_constraint_already_in_unique_together() -> None:
    """Do not emit a second UNIQUE for UniqueConstraint fields already in unique_together."""

    class WidgetConstrained(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100)
        category = fields.CharField(max_length=50)

        class Meta:
            table = "widget"
            app = "models"
            unique_together = (("name", "category"),)
            constraints = [
                UniqueConstraint(fields=("name", "category"), name="uid_name_category"),
            ]

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    await editor.create_model(WidgetConstrained)

    sql = client.executed[0]
    assert "uid_name_category" not in sql
    assert sql.count("UNIQUE") == 1


@pytest.mark.asyncio
async def test_create_model_skips_unique_constraint_matching_unique_together_columns() -> None:
    """Skip UniqueConstraint when its resolved columns match unique_together."""

    class Organization(Model):
        id = fields.IntField(pk=True)

        class Meta:
            table = "organization"
            app = "models"

    class Membership(Model):
        id = fields.IntField(pk=True)
        organization: fields.ForeignKeyRelation[Organization] = fields.ForeignKeyField(
            "models.Organization", related_name="memberships"
        )
        user_email = fields.CharField(max_length=255)

        class Meta:
            table = "membership"
            app = "models"
            unique_together = (("organization", "user_email"),)
            constraints = [
                UniqueConstraint(fields=("organization_id", "user_email"), name="uid_org_email"),
            ]

    init_apps(Organization, Membership)

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    await editor.create_model(Membership)

    sql = client.executed[0]
    assert "uid_org_email" not in sql
    assert sql.count("UNIQUE") == 1


@pytest.mark.asyncio
async def test_mysql_create_model_uses_named_unique_key() -> None:
    """MySQL CREATE TABLE must use the UniqueConstraint name as UNIQUE KEY."""

    class Like(Model):
        id = fields.IntField(pk=True)
        types = fields.CharField(max_length=10)
        user_id = fields.IntField()
        art_id = fields.IntField()
        score = fields.IntField()

        class Meta:
            table = "like"
            app = "models"
            constraints = [
                UniqueConstraint(fields=("types", "user_id", "art_id"), name="unique_like"),
                CheckConstraint(check="score >= 0", name="chk_score_positive"),
            ]

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.create_model(Like)

    sql = client.executed[0]
    assert "UNIQUE KEY `unique_like` (`types`, `user_id`, `art_id`)" in sql
    assert "CONSTRAINT `chk_score_positive` CHECK (score >= 0)" in sql


@pytest.mark.asyncio
async def test_create_model_postgres_partial_unique_index() -> None:
    """PostgreSQL CREATE TABLE emits partial UniqueConstraint as CREATE UNIQUE INDEX."""

    class UserAccount(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255)
        is_active = fields.BooleanField(default=True)

        class Meta:
            table = "user_account"
            app = "models"
            constraints = [
                UniqueConstraint(
                    fields=("email",), name="uq_active_email", condition="is_active = true"
                ),
            ]

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    await editor.create_model(UserAccount)

    sql = client.executed[0]
    assert (
        'CREATE UNIQUE INDEX "uq_active_email" ON "user_account" ("email") WHERE is_active = true;'
    ) in sql


def test_generate_schema_includes_meta_constraints() -> None:
    """generate_schemas CREATE TABLE must include Meta.constraints."""

    class Like(Model):
        id = fields.IntField(pk=True)
        types = fields.CharField(max_length=10)
        user_id = fields.IntField()
        art_id = fields.IntField()
        score = fields.IntField()

        class Meta:
            table = "like"
            app = "models"
            constraints = [
                UniqueConstraint(fields=("types", "user_id", "art_id"), name="unique_like"),
                CheckConstraint(check="score >= 0", name="chk_score_positive"),
            ]

    generator = BaseSchemaGenerator(FakeClient("sql"))
    sql = generator._get_table_sql(Like, safe=False)["table_creation_string"]
    assert 'CONSTRAINT "unique_like" UNIQUE ("types", "user_id", "art_id")' in sql
    assert 'CONSTRAINT "chk_score_positive" CHECK (score >= 0)' in sql
