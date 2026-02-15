"""Backend-specific schema editor tests: bool defaults, ALTER COLUMN, FK handling, quoting."""

from __future__ import annotations

from typing import Any

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.fields.relational import ForeignKeyFieldInstance
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
from tortoise.migrations.schema_editor.mssql import MSSQLSchemaEditor
from tortoise.migrations.schema_editor.mysql import MySQLSchemaEditor
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


class TestSchemaEditor(BaseSchemaEditor):
    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return ""

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return ""


def init_apps(*models: type[Model]) -> None:
    apps = StateApps()
    for model in models:
        apps.register_model("models", model)
    apps._init_relations()


# ---------------------------------------------------------------------------
# BooleanField db_default escaping tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_bool_db_default_true() -> None:
    """PostgreSQL should emit DEFAULT TRUE for BooleanField(db_default=True)."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        is_active = fields.BooleanField(db_default=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    await editor.add_field(Widget, "is_active")

    assert client.executed
    assert "DEFAULT TRUE" in client.executed[0]


@pytest.mark.asyncio
async def test_postgres_bool_db_default_false() -> None:
    """PostgreSQL should emit DEFAULT FALSE for BooleanField(db_default=False)."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        is_active = fields.BooleanField(db_default=False)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    await editor.add_field(Widget, "is_active")

    assert client.executed
    assert "DEFAULT FALSE" in client.executed[0]


@pytest.mark.asyncio
async def test_base_editor_bool_db_default_still_uses_integer() -> None:
    """Non-PostgreSQL backends should still emit DEFAULT 1 for BooleanField(db_default=True)."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        is_active = fields.BooleanField(db_default=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    await editor.add_field(Widget, "is_active")

    assert client.executed
    assert "DEFAULT 1" in client.executed[0]


@pytest.mark.asyncio
async def test_postgres_int_db_default_unaffected() -> None:
    """PostgreSQL non-bool db_default should still work (regression guard)."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField(db_default=0)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    await editor.add_field(Widget, "stock")

    assert client.executed
    assert "DEFAULT 0" in client.executed[0]


@pytest.mark.asyncio
async def test_mssql_bool_db_default_still_uses_integer() -> None:
    """MSSQL (BIT column) should still emit DEFAULT 1 for BooleanField(db_default=True)."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        is_active = fields.BooleanField(db_default=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)
    await editor.add_field(Widget, "is_active")

    assert client.executed
    assert "DEFAULT 1" in client.executed[0]


@pytest.mark.asyncio
async def test_postgres_alter_field_bool_db_default() -> None:
    """PostgreSQL alter_field adding db_default=True should emit SET DEFAULT TRUE."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        is_active = fields.BooleanField(default=True)

        class Meta:
            table = "widget"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        is_active = fields.BooleanField(default=True, db_default=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "is_active")

    assert client.executed
    set_default_sqls = [sql for sql in client.executed if "DEFAULT" in sql]
    assert set_default_sqls, f"Expected SET DEFAULT SQL, got: {client.executed}"
    assert "TRUE" in set_default_sqls[0]


# ---------------------------------------------------------------------------
# MySQL ALTER COLUMN tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mysql_alter_field_null_to_not_null() -> None:
    """MySQL should use MODIFY COLUMN with type for null->not-null change."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        budget = fields.DecimalField(null=True, max_digits=12, decimal_places=2)

        class Meta:
            table = "department"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        budget = fields.DecimalField(max_digits=12, decimal_places=2)

        class Meta:
            table = "department"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "budget")

    assert client.executed
    sql = client.executed[0]
    assert "MODIFY COLUMN" in sql
    assert "`budget`" in sql
    assert "NOT NULL" in sql


@pytest.mark.asyncio
async def test_mysql_alter_field_not_null_to_null() -> None:
    """MySQL should use MODIFY COLUMN with type for not-null->null change."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        budget = fields.DecimalField(max_digits=12, decimal_places=2)

        class Meta:
            table = "department"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        budget = fields.DecimalField(null=True, max_digits=12, decimal_places=2)

        class Meta:
            table = "department"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "budget")

    assert client.executed
    sql = client.executed[0]
    assert "MODIFY COLUMN" in sql
    assert "`budget`" in sql
    assert "NULL" in sql
    assert "NOT NULL" not in sql


@pytest.mark.asyncio
async def test_mysql_alter_field_set_default() -> None:
    """MySQL SET DEFAULT should use backtick quoting."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField()

        class Meta:
            table = "product"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField(db_default=10)

        class Meta:
            table = "product"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "stock")

    assert client.executed
    sql = client.executed[0]
    assert "ALTER COLUMN `stock` SET DEFAULT" in sql
    assert '"stock"' not in sql  # No double-quote quoting


# ---------------------------------------------------------------------------
# MSSQL ALTER COLUMN tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mssql_alter_field_null_to_not_null() -> None:
    """MSSQL should use ALTER COLUMN [col] type NOT NULL for nullability change."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        budget = fields.DecimalField(null=True, max_digits=12, decimal_places=2)

        class Meta:
            table = "department"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        budget = fields.DecimalField(max_digits=12, decimal_places=2)

        class Meta:
            table = "department"
            app = "models"

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "budget")

    assert client.executed
    sql = client.executed[0]
    assert "ALTER COLUMN [budget]" in sql
    assert "NOT NULL" in sql
    assert "SET NOT NULL" not in sql  # MSSQL doesn't use SET NOT NULL


@pytest.mark.asyncio
async def test_mssql_alter_field_set_default() -> None:
    """MSSQL should use ADD DEFAULT ... FOR [col] instead of ALTER COLUMN SET DEFAULT."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField()

        class Meta:
            table = "product"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField(db_default=10)

        class Meta:
            table = "product"
            app = "models"

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "stock")

    assert client.executed
    sql = client.executed[0]
    assert "ADD DEFAULT" in sql
    assert "FOR [stock]" in sql


@pytest.mark.asyncio
async def test_mssql_alter_field_drop_default() -> None:
    """MSSQL should use dynamic SQL to find and drop default constraint."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField(db_default=10)

        class Meta:
            table = "product"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField()

        class Meta:
            table = "product"
            app = "models"

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "stock")

    assert client.executed
    sql = client.executed[0]
    assert "sys.default_constraints" in sql
    assert "DROP CONSTRAINT" in sql


# ---------------------------------------------------------------------------
# MSSQL self-referencing FK tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mssql_self_referencing_fk_downgrades_cascade() -> None:
    """MSSQL should use NO ACTION for self-referencing FK instead of CASCADE."""

    class Department(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=150)
        parent: ForeignKeyFieldInstance[Any] | None = fields.ForeignKeyField(
            "models.Department",
            source_field="parent_id",
            null=True,
            related_name="children",
        )

        class Meta:
            table = "department"
            app = "models"

    init_apps(Department)

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)
    await editor.create_model(Department)

    assert client.executed
    sql = client.executed[0]
    assert "NO ACTION" in sql
    assert "ON DELETE CASCADE" not in sql


@pytest.mark.asyncio
async def test_mssql_non_self_referencing_fk_keeps_cascade() -> None:
    """MSSQL should keep CASCADE for non-self-referencing FKs."""

    class Company(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=300)

        class Meta:
            table = "company"
            app = "models"

    class Department(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=150)
        company: ForeignKeyFieldInstance[Any] = fields.ForeignKeyField(
            "models.Company",
            source_field="company_id",
            related_name="departments",
        )

        class Meta:
            table = "department"
            app = "models"

    init_apps(Company, Department)

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)
    await editor.create_model(Department)

    assert client.executed
    sql = client.executed[0]
    assert "ON DELETE CASCADE" in sql


# ---------------------------------------------------------------------------
# MSSQL template quoting tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mssql_delete_constraint_uses_brackets() -> None:
    """MSSQL DELETE_CONSTRAINT_TEMPLATE should use bracket quoting."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255, unique=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)
    constraint = UniqueConstraint(fields=("email",))
    await editor.remove_constraint(Widget, constraint)

    assert client.executed
    sql = client.executed[0]
    # Should use brackets, not double quotes
    assert "DROP CONSTRAINT [" in sql
    assert 'DROP CONSTRAINT "' not in sql


@pytest.mark.asyncio
async def test_mssql_unique_constraint_create_uses_brackets() -> None:
    """MSSQL UNIQUE_CONSTRAINT_CREATE_TEMPLATE should use bracket quoting."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("mssql", inline_comment=False)
    editor = MSSQLSchemaEditor(client)
    constraint = UniqueConstraint(fields=("email",))
    await editor.add_constraint(Widget, constraint)

    assert client.executed
    sql = client.executed[0]
    assert "CONSTRAINT [" in sql
    assert 'CONSTRAINT "' not in sql


# ---------------------------------------------------------------------------
# RandomHex dialect-aware default tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_random_hex_produces_dialect_specific_sql() -> None:
    """RandomHex should produce different SQL for each dialect."""
    from tortoise.fields.db_defaults import RandomHex

    rh = RandomHex()
    assert "randomblob" in rh.get_sql(dialect="sqlite")
    assert "md5(random" in rh.get_sql(dialect="postgres")
    assert "RANDOM_BYTES" in rh.get_sql(dialect="mysql")
    assert "HASHBYTES" in rh.get_sql(dialect="mssql")
    assert "SYS_GUID" in rh.get_sql(dialect="oracle")
