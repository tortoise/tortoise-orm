"""Integration tests for schema-qualified table names in migration schema editors.

Covers:
- Schema-qualified DDL generation per dialect (collect_sql mode)
- CreateSchema / DropSchema operations
- Autodetector schema detection
- MigrationWriter serialization of schema operations
- through_schema query-time behavior (filters, joins, add/remove)
"""

from __future__ import annotations

import copy
from typing import Any, cast

import pytest
from pypika_tortoise import Table

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.fields.relational import (
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    ManyToManyRelation,
)
from tortoise.filters import get_m2m_filters
from tortoise.migrations.operations import (
    CreateModel,
    CreateSchema,
    DeleteModel,
    DropSchema,
)
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
from tortoise.migrations.schema_editor.mssql import MSSQLSchemaEditor
from tortoise.migrations.schema_editor.mysql import MySQLSchemaEditor
from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor
from tortoise.migrations.schema_editor.sqlite import SqliteSchemaEditor
from tortoise.migrations.schema_generator.operation_generator import OperationGenerator
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.migrations.writer import MigrationWriter
from tortoise.models import Model
from tortoise.query_utils import get_joins_for_related_field


def init_apps(*models: type[Model]) -> None:
    apps = StateApps()
    for model in models:
        apps.register_model("models", model)
    apps._init_relations()


# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------


def _make_schema_models() -> tuple[type[Model], type[Model], type[Model], type[Model]]:
    """Build models with Meta.schema='custom' for testing."""

    class SchemaCategory(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()

        class Meta:
            app = "models"
            table = "category"
            schema = "custom"

    class SchemaProduct(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
        category: ForeignKeyFieldInstance[Any] = fields.ForeignKeyField(
            "models.SchemaCategory", related_name="products"
        )

        class Meta:
            app = "models"
            table = "product"
            schema = "custom"

    class SchemaTag(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()

        class Meta:
            app = "models"
            table = "tag"
            schema = "custom"

    class SchemaProductWithTags(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
        tags: ManyToManyRelation[Any] = fields.ManyToManyField(
            "models.SchemaTag", related_name="products"
        )

        class Meta:
            app = "models"
            table = "product"
            schema = "custom"

    init_apps(SchemaCategory, SchemaProduct)
    init_apps(SchemaTag, SchemaProductWithTags)
    return SchemaCategory, SchemaProduct, SchemaTag, SchemaProductWithTags


# ---------------------------------------------------------------------------
# 1. Schema-qualified DDL per dialect
# ---------------------------------------------------------------------------


class _TestEditor(BaseSchemaEditor):
    """Minimal concrete editor for tests (base ANSI SQL dialect)."""

    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return ""

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return ""


@pytest.mark.asyncio
async def test_base_create_model_with_schema() -> None:
    """Base editor qualifies CREATE TABLE with schema."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("sql")
    editor = _TestEditor(client)

    await editor.create_model(SchemaCategory)

    sql = client.executed[0]
    assert 'CREATE TABLE "custom"."category"' in sql


@pytest.mark.asyncio
async def test_base_create_model_without_schema() -> None:
    """Without Meta.schema, output is unchanged (backward compatible)."""

    class PlainWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()

        class Meta:
            app = "models"
            table = "widget"

    client = FakeClient("sql")
    editor = _TestEditor(client)
    await editor.create_model(PlainWidget)

    sql = client.executed[0]
    assert 'CREATE TABLE "widget"' in sql
    assert '"custom"' not in sql


@pytest.mark.asyncio
async def test_base_fk_references_qualified() -> None:
    """FK REFERENCES uses schema-qualified target table."""
    _, SchemaProduct, *_ = _make_schema_models()
    client = FakeClient("sql")
    editor = _TestEditor(client)

    await editor.create_model(SchemaProduct)

    sql = client.executed[0]
    assert 'REFERENCES "custom"."category"' in sql


@pytest.mark.asyncio
async def test_base_m2m_table_qualified() -> None:
    """M2M through table is schema-qualified."""
    *_, SchemaTag, SchemaProductWithTags = _make_schema_models()
    client = FakeClient("sql")
    editor = _TestEditor(client)

    await editor.create_model(SchemaProductWithTags)

    combined = "\n".join(client.executed)
    assert 'CREATE TABLE "custom"."product_tag"' in combined


@pytest.mark.asyncio
async def test_base_delete_model_qualified() -> None:
    """DROP TABLE uses schema-qualified name."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("sql")
    editor = _TestEditor(client)

    await editor.delete_model(SchemaCategory)

    sql = client.executed[0]
    assert 'DROP TABLE "custom"."category"' in sql


@pytest.mark.asyncio
async def test_base_add_field_qualified() -> None:
    """ALTER TABLE ADD COLUMN uses schema-qualified name."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("sql")
    editor = _TestEditor(client)

    await editor.add_field(SchemaCategory, "name")

    sql = client.executed[0]
    assert 'ALTER TABLE "custom"."category" ADD COLUMN' in sql


@pytest.mark.asyncio
async def test_base_rename_table_qualified() -> None:
    """RENAME TABLE uses schema-qualified names."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("sql")
    editor = _TestEditor(client)

    await editor.rename_table(SchemaCategory, "category", "categories")

    sql = client.executed[0]
    assert '"custom"."category"' in sql
    assert '"custom"."categories"' in sql


# ---------------------------------------------------------------------------
# 2. Per-dialect schema qualification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_create_table_with_schema() -> None:
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    await editor.create_model(SchemaCategory)

    sql = client.executed[0]
    assert 'CREATE TABLE "custom"."category"' in sql


@pytest.mark.asyncio
async def test_mysql_create_table_with_schema() -> None:
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("mysql", inline_comment=True, charset="utf8mb4")
    editor = MySQLSchemaEditor(client)

    await editor.create_model(SchemaCategory)

    sql = client.executed[0]
    assert "CREATE TABLE `custom`.`category`" in sql


@pytest.mark.asyncio
async def test_mssql_create_table_with_schema() -> None:
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)

    await editor.create_model(SchemaCategory)

    sql = client.executed[0]
    assert "CREATE TABLE [custom].[category]" in sql


@pytest.mark.asyncio
async def test_oracle_create_table_with_schema() -> None:
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("oracle", inline_comment=False)
    editor = OracleSchemaEditor(client)

    await editor.create_model(SchemaCategory)

    sql = client.executed[0]
    assert 'CREATE TABLE "custom"."category"' in sql


@pytest.mark.asyncio
async def test_sqlite_ignores_schema() -> None:
    """SQLite ignores schema — table name has no schema prefix."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("sqlite", inline_comment=True)
    editor = SqliteSchemaEditor(client)

    await editor.create_model(SchemaCategory)

    sql = client.executed[0]
    assert 'CREATE TABLE "category"' in sql
    assert '"custom"' not in sql


# ---------------------------------------------------------------------------
# 3. CreateSchema / DropSchema operations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_schema_postgres() -> None:
    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    await editor.create_schema("custom")

    assert client.executed == ['CREATE SCHEMA IF NOT EXISTS "custom";']


@pytest.mark.asyncio
async def test_drop_schema_postgres() -> None:
    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    await editor.drop_schema("custom")

    assert client.executed == ['DROP SCHEMA IF EXISTS "custom" CASCADE;']


@pytest.mark.asyncio
async def test_create_schema_mssql() -> None:
    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)

    await editor.create_schema("custom")

    assert len(client.executed) == 1
    assert "CREATE SCHEMA [custom]" in client.executed[0]
    assert "IF NOT EXISTS" in client.executed[0]


@pytest.mark.asyncio
async def test_create_schema_noop_for_base() -> None:
    """Base editor's create_schema is a no-op."""
    client = FakeClient("sql")
    editor = _TestEditor(client)

    await editor.create_schema("custom")

    assert client.executed == []


@pytest.mark.asyncio
async def test_create_schema_operation_runs(empty_state: State) -> None:
    """CreateSchema operation calls schema_editor.create_schema()."""
    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    op = CreateSchema(schema_name="custom")
    await op.run("models", empty_state, dry_run=False, state_editor=editor)

    assert 'CREATE SCHEMA IF NOT EXISTS "custom";' in client.executed


@pytest.mark.asyncio
async def test_drop_schema_operation_runs(empty_state: State) -> None:
    """DropSchema operation calls schema_editor.drop_schema()."""
    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    op = DropSchema(schema_name="custom")
    await op.run("models", empty_state, dry_run=False, state_editor=editor)

    assert 'DROP SCHEMA IF EXISTS "custom" CASCADE;' in client.executed


@pytest.mark.asyncio
async def test_create_schema_operation_backward(empty_state: State) -> None:
    """CreateSchema backward calls drop_schema."""
    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    op = CreateSchema(schema_name="custom")
    old_state = empty_state.clone()
    op.state_forward("models", empty_state)
    await op.database_backward("models", old_state, empty_state, editor)

    assert 'DROP SCHEMA IF EXISTS "custom" CASCADE;' in client.executed


def test_create_schema_describe() -> None:
    op = CreateSchema(schema_name="custom")
    assert op.describe() == "Create schema custom"


def test_drop_schema_describe() -> None:
    op = DropSchema(schema_name="custom")
    assert op.describe() == "Drop schema custom"


# ---------------------------------------------------------------------------
# 4. Autodetector schema detection
# ---------------------------------------------------------------------------


def _build_state_with_schema_model(state: State, schema: str | None = None) -> None:
    """Add a model with optional schema to a state."""
    options: dict[str, Any] = {"table": "product", "app": "models"}
    if schema:
        options["schema"] = schema
    CreateModel(
        name="Product",
        fields=[("id", fields.IntField(pk=True))],
        options=options,
    ).state_forward("models", state)


def test_autodetector_generates_create_schema() -> None:
    """When a model with new schema appears, CreateSchema is emitted."""
    old_state = State(models={}, apps=StateApps())
    new_state = State(models={}, apps=StateApps())
    _build_state_with_schema_model(new_state, schema="custom")

    ops = OperationGenerator(old_state, new_state).generate()

    assert len(ops) >= 2
    assert isinstance(ops[0], CreateSchema)
    assert ops[0].schema_name == "custom"
    assert isinstance(ops[1], CreateModel)


def test_autodetector_generates_drop_schema() -> None:
    """When a schema is no longer used, DropSchema is emitted."""
    old_state = State(models={}, apps=StateApps())
    new_state = State(models={}, apps=StateApps())
    _build_state_with_schema_model(old_state, schema="custom")

    ops = OperationGenerator(old_state, new_state).generate()

    assert len(ops) >= 2
    assert isinstance(ops[0], DeleteModel)
    assert isinstance(ops[1], DropSchema)
    assert ops[1].schema_name == "custom"


def test_autodetector_no_duplicate_schemas() -> None:
    """Two models in the same schema produce only one CreateSchema."""
    old_state = State(models={}, apps=StateApps())
    new_state = State(models={}, apps=StateApps())

    CreateModel(
        name="Product",
        fields=[("id", fields.IntField(pk=True))],
        options={"table": "product", "app": "models", "schema": "custom"},
    ).state_forward("models", new_state)
    CreateModel(
        name="Category",
        fields=[("id", fields.IntField(pk=True))],
        options={"table": "category", "app": "models", "schema": "custom"},
    ).state_forward("models", new_state)

    ops = OperationGenerator(old_state, new_state).generate()

    schema_ops = [op for op in ops if isinstance(op, CreateSchema)]
    assert len(schema_ops) == 1
    assert schema_ops[0].schema_name == "custom"


def test_autodetector_no_schema_ops_for_plain_models() -> None:
    """Models without schema produce no schema operations."""
    old_state = State(models={}, apps=StateApps())
    new_state = State(models={}, apps=StateApps())
    _build_state_with_schema_model(new_state, schema=None)

    ops = OperationGenerator(old_state, new_state).generate()

    schema_ops = [op for op in ops if isinstance(op, (CreateSchema, DropSchema))]
    assert len(schema_ops) == 0


def test_autodetector_multiple_schemas_sorted() -> None:
    """Multiple new schemas are created in sorted order."""
    old_state = State(models={}, apps=StateApps())
    new_state = State(models={}, apps=StateApps())

    CreateModel(
        name="Product",
        fields=[("id", fields.IntField(pk=True))],
        options={"table": "product", "app": "models", "schema": "warehouse"},
    ).state_forward("models", new_state)
    CreateModel(
        name="Category",
        fields=[("id", fields.IntField(pk=True))],
        options={"table": "category", "app": "models", "schema": "catalog"},
    ).state_forward("models", new_state)

    ops = OperationGenerator(old_state, new_state).generate()

    schema_ops = [op for op in ops if isinstance(op, CreateSchema)]
    assert len(schema_ops) == 2
    assert schema_ops[0].schema_name == "catalog"
    assert schema_ops[1].schema_name == "warehouse"


# ---------------------------------------------------------------------------
# 5. MigrationWriter serialization
# ---------------------------------------------------------------------------


def test_writer_serializes_create_schema() -> None:
    writer = MigrationWriter(
        name="0001_initial",
        app_label="models",
        operations=[CreateSchema(schema_name="custom")],
    )
    output = writer.as_string()
    assert "ops.CreateSchema(schema_name='custom')" in output


def test_writer_serializes_drop_schema() -> None:
    writer = MigrationWriter(
        name="0002_drop",
        app_label="models",
        operations=[DropSchema(schema_name="custom")],
    )
    output = writer.as_string()
    assert "ops.DropSchema(schema_name='custom')" in output


def test_writer_schema_with_create_model() -> None:
    """Full migration with CreateSchema + CreateModel serializes correctly."""
    writer = MigrationWriter(
        name="0001_initial",
        app_label="models",
        operations=[
            CreateSchema(schema_name="custom"),
            CreateModel(
                name="Product",
                fields=[("id", fields.IntField(pk=True))],
                options={"table": "product", "schema": "custom"},
            ),
        ],
    )
    output = writer.as_string()
    assert "ops.CreateSchema(schema_name='custom')" in output
    assert "ops.CreateModel(" in output
    # CreateSchema should come before CreateModel
    schema_pos = output.index("CreateSchema")
    model_pos = output.index("CreateModel")
    assert schema_pos < model_pos


# ---------------------------------------------------------------------------
# 6. MSSQL sp_rename schema-qualified bug (Issue 1 from code review)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mssql_rename_table_with_schema() -> None:
    """MSSQL sp_rename second argument must be unqualified new name."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)

    await editor.rename_table(SchemaCategory, "category", "categories")

    sql = client.executed[0]
    # First arg: schema-qualified old name
    assert "[custom].[category]" in sql
    # Second arg: must be unqualified new name (not [custom].[categories])
    assert "categories'" in sql or "categories," in sql
    assert "[custom].[categories]" not in sql


@pytest.mark.asyncio
async def test_mssql_rename_table_without_schema() -> None:
    """MSSQL sp_rename without schema should still work."""

    class PlainItem(Model):
        id = fields.IntField(pk=True)

        class Meta:
            app = "models"
            table = "item"

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)

    await editor.rename_table(PlainItem, "item", "items")

    sql = client.executed[0]
    assert "sp_rename" in sql
    assert "[item]" in sql
    assert "items" in sql


# ---------------------------------------------------------------------------
# 7. MSSQL remove_field cleanup SQL must filter by schema (Issue 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mssql_remove_field_cleanup_sql_filters_schema() -> None:
    """MSSQL remove_field cleanup SQL should filter sys.tables by schema."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)

    name_field = SchemaCategory._meta.fields_map["name"]
    await editor.remove_field(SchemaCategory, name_field)

    # The cleanup SQL (first executed statement) queries sys.tables.
    # When a schema is set, it must filter by schema to avoid ambiguity.
    cleanup_sql = client.executed[0]
    assert "sys.schemas" in cleanup_sql
    assert "'custom'" in cleanup_sql


# ---------------------------------------------------------------------------
# 8. ALTER TABLE / REMOVE uses schema-qualified names per dialect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mssql_alter_field_qualified() -> None:
    """MSSQL ALTER TABLE uses schema-qualified name."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)

    old_field = SchemaCategory._meta.fields_map["name"]
    new_field = copy.copy(old_field)
    new_field.null = True  # change from NOT NULL to NULL

    await editor._alter_field(SchemaCategory, old_field, new_field)

    combined = " ".join(client.executed)
    assert "[custom].[category]" in combined


@pytest.mark.asyncio
async def test_mssql_delete_model_qualified() -> None:
    """MSSQL DROP TABLE uses schema-qualified name."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)

    await editor.delete_model(SchemaCategory)

    sql = client.executed[0]
    assert "DROP TABLE [custom].[category]" in sql


@pytest.mark.asyncio
async def test_mysql_rename_table_with_schema() -> None:
    """MySQL RENAME TABLE uses schema-qualified names on both sides."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("mysql", inline_comment=True, charset="utf8mb4")
    editor = MySQLSchemaEditor(client)

    await editor.rename_table(SchemaCategory, "category", "categories")

    sql = client.executed[0]
    assert "`custom`.`category`" in sql
    assert "`custom`.`categories`" in sql


@pytest.mark.asyncio
async def test_oracle_rename_table_with_schema() -> None:
    """Oracle RENAME TABLE uses schema-qualified names."""
    SchemaCategory, *_ = _make_schema_models()
    client = FakeClient("oracle", inline_comment=False)
    editor = OracleSchemaEditor(client)

    await editor.rename_table(SchemaCategory, "category", "categories")

    sql = client.executed[0]
    assert '"custom"."category"' in sql
    assert '"custom"."categories"' in sql


# ---------------------------------------------------------------------------
# 9. through_schema query-time behavior (Issue 3 from code review)
# ---------------------------------------------------------------------------


def _make_m2m_models_with_schema() -> tuple[type[Model], type[Model]]:
    """Build M2M models with Meta.schema for through_schema testing."""

    class STag(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()

        class Meta:
            app = "models"
            table = "tag"
            schema = "catalog"

    class SArticle(Model):
        id = fields.IntField(pk=True)
        title = fields.TextField()
        tags: ManyToManyRelation[Any] = fields.ManyToManyField(
            "models.STag", related_name="articles", through="article_tag"
        )

        class Meta:
            app = "models"
            table = "article"
            schema = "catalog"

    init_apps(STag, SArticle)
    return STag, SArticle


def test_through_schema_set_on_forward_m2m_field() -> None:
    """Forward M2M field gets through_schema from declaring model."""
    _, SArticle = _make_m2m_models_with_schema()
    field = cast(ManyToManyFieldInstance, SArticle._meta.fields_map["tags"])
    assert field.through_schema == "catalog"


def test_through_schema_set_on_backward_m2m_field() -> None:
    """Backward (auto-generated) M2M field gets through_schema from declaring model."""
    STag, _ = _make_m2m_models_with_schema()
    field = cast(ManyToManyFieldInstance, STag._meta.fields_map["articles"])
    assert field._generated is True
    assert field.through_schema == "catalog"


def test_through_schema_none_without_schema() -> None:
    """M2M field without Meta.schema has through_schema=None."""

    class PlainA(Model):
        id = fields.IntField(pk=True)

        class Meta:
            app = "models"
            table = "plain_a"

    class PlainB(Model):
        id = fields.IntField(pk=True)
        a_items: ManyToManyRelation[Any] = fields.ManyToManyField(
            "models.PlainA", related_name="b_items"
        )

        class Meta:
            app = "models"
            table = "plain_b"

    init_apps(PlainA, PlainB)
    field = cast(ManyToManyFieldInstance, PlainB._meta.fields_map["a_items"])
    assert field.through_schema is None


def test_get_m2m_filters_includes_schema_on_table() -> None:
    """get_m2m_filters() produces Table objects with schema set."""
    _, SArticle = _make_m2m_models_with_schema()
    field = cast(ManyToManyFieldInstance, SArticle._meta.fields_map["tags"])

    filters = get_m2m_filters("tags", field)

    for filter_name in ("tags", "tags__not", "tags__in", "tags__not_in"):
        table: Table = filters[filter_name]["table"]
        assert table._schema is not None, f"{filter_name}: schema should not be None"
        assert table._schema._name == "catalog", f"{filter_name}: expected schema='catalog'"
        assert table._table_name == "article_tag"


def test_get_joins_for_m2m_field_includes_schema() -> None:
    """get_joins_for_related_field() creates through Table with schema."""
    _, SArticle = _make_m2m_models_with_schema()
    field = cast(ManyToManyFieldInstance, SArticle._meta.fields_map["tags"])

    base_table = Table("article", schema="catalog")
    joins = get_joins_for_related_field(base_table, field, "tags")

    # First join is to through table
    through_table = joins[0][0]
    assert through_table._table_name == "article_tag"
    assert through_table._schema is not None
    assert through_table._schema._name == "catalog"


def test_get_joins_for_backward_m2m_field_includes_schema() -> None:
    """Backward M2M field's through table also gets schema."""
    STag, _ = _make_m2m_models_with_schema()
    field = cast(ManyToManyFieldInstance, STag._meta.fields_map["articles"])

    base_table = Table("tag", schema="catalog")
    joins = get_joins_for_related_field(base_table, field, "articles")

    through_table = joins[0][0]
    assert through_table._table_name == "article_tag"
    assert through_table._schema is not None
    assert through_table._schema._name == "catalog"
