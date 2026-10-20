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

    assert len(client.executed) == 1
    assert (
        client.executed[0]
        == 'ALTER TABLE "widget" ADD COLUMN "is_active" BOOL NOT NULL DEFAULT TRUE'
    )


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

    assert len(client.executed) == 1
    assert (
        client.executed[0]
        == 'ALTER TABLE "widget" ADD COLUMN "is_active" BOOL NOT NULL DEFAULT FALSE'
    )


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

    assert len(client.executed) == 1
    assert (
        client.executed[0] == 'ALTER TABLE "widget" ADD COLUMN "is_active" BOOL NOT NULL DEFAULT 1'
    )


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

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" ADD COLUMN "stock" INT NOT NULL DEFAULT 0'


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

    assert len(client.executed) == 1
    assert client.executed[0] == "ALTER TABLE [widget] ADD [is_active] BIT NOT NULL DEFAULT 1"


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

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" ALTER COLUMN "is_active" SET DEFAULT TRUE'


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

    assert len(client.executed) == 1
    assert (
        client.executed[0]
        == "ALTER TABLE `department` MODIFY COLUMN `budget` DECIMAL(12,2) NOT NULL"
    )


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

    assert len(client.executed) == 1
    assert (
        client.executed[0] == "ALTER TABLE `department` MODIFY COLUMN `budget` DECIMAL(12,2) NULL"
    )


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

    assert len(client.executed) == 1
    assert client.executed[0] == "ALTER TABLE `product` ALTER COLUMN `stock` SET DEFAULT (10)"


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

    assert len(client.executed) == 1
    assert (
        client.executed[0]
        == "ALTER TABLE [department] ALTER COLUMN [budget] DECIMAL(12,2) NOT NULL"
    )


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

    assert len(client.executed) == 1
    assert client.executed[0] == "ALTER TABLE [product] ADD DEFAULT 10 FOR [stock]"


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

    assert len(client.executed) == 1
    assert client.executed[0] == (
        "DECLARE @sql NVARCHAR(MAX) = N'';\n"
        "SELECT @sql = N'ALTER TABLE [' + s.name + '].[' + t.name + ']"
        " DROP CONSTRAINT [' + dc.name + ']'\n"
        "FROM sys.default_constraints dc\n"
        "JOIN sys.columns c ON dc.parent_object_id = c.object_id"
        " AND dc.parent_column_id = c.column_id\n"
        "JOIN sys.tables t ON dc.parent_object_id = t.object_id\n"
        "JOIN sys.schemas s ON t.schema_id = s.schema_id\n"
        "WHERE t.name = 'product' AND c.name = 'stock';\n"
        "IF @sql <> N'' EXEC sp_executesql @sql;"
    )


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

    assert len(client.executed) == 1
    assert client.executed[0] == (
        "CREATE TABLE [department] (\n"
        "    [id] INT IDENTITY(1,1) NOT NULL PRIMARY KEY,\n"
        "    [name] VARCHAR(150) NOT NULL,\n"
        "    [parent_id] INT,\n"
        "    CONSTRAINT [fk_departme_departme_ba94d121] FOREIGN KEY ([parent_id])"
        " REFERENCES [department] ([id]) ON DELETE NO ACTION\n"
        ");"
    )


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

    assert len(client.executed) == 1
    assert client.executed[0] == (
        "CREATE TABLE [department] (\n"
        "    [id] INT IDENTITY(1,1) NOT NULL PRIMARY KEY,\n"
        "    [name] VARCHAR(150) NOT NULL,\n"
        "    [company_id] INT NOT NULL,\n"
        "    CONSTRAINT [fk_departme_company_0e6b7be6] FOREIGN KEY ([company_id])"
        " REFERENCES [company] ([id]) ON DELETE CASCADE\n"
        ");"
    )


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

    assert len(client.executed) == 1
    assert client.executed[0] == "ALTER TABLE [widget] DROP CONSTRAINT [uid_widget_email_3d71d7]"


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

    assert len(client.executed) == 1
    assert (
        client.executed[0]
        == "ALTER TABLE [widget] ADD CONSTRAINT [uid_widget_email_3d71d7] UNIQUE ([email])"
    )


# ---------------------------------------------------------------------------
# RandomHex dialect-aware default tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_random_hex_produces_dialect_specific_sql() -> None:
    """RandomHex should produce different SQL for each dialect."""
    from tortoise.fields.db_defaults import RandomHex

    rh = RandomHex()
    assert rh.get_sql(dialect="sqlite") == "(lower(hex(randomblob(16))))"
    assert rh.get_sql(dialect="postgres") == "md5(random()::text)"
    assert rh.get_sql(dialect="mysql") == "(LOWER(HEX(RANDOM_BYTES(16))))"
    assert rh.get_sql(dialect="mssql") == (
        "(LOWER(CONVERT(VARCHAR(32), HASHBYTES('MD5', CAST(NEWID() AS NVARCHAR(36))), 2)))"
    )
    assert rh.get_sql(dialect="oracle") == "LOWER(RAWTOHEX(SYS_GUID()))"


# ---------------------------------------------------------------------------
# MySQL add_field with SqlDefault expression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mysql_add_field_with_sql_default_expression() -> None:
    """MySQL add_field with SqlDefault should split into ADD COLUMN + ALTER SET DEFAULT."""
    from tortoise.fields.db_defaults import Now

    class Widget(Model):
        id = fields.IntField(pk=True)
        created_at = fields.DatetimeField(db_default=Now())

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.add_field(Widget, "created_at")

    assert len(client.executed) == 2
    assert client.executed[0] == "ALTER TABLE `widget` ADD COLUMN `created_at` DATETIME(6) NOT NULL"
    assert client.executed[1] == (
        "ALTER TABLE `widget` ALTER COLUMN `created_at` SET DEFAULT (CURRENT_TIMESTAMP(6))"
    )


# ---------------------------------------------------------------------------
# Oracle FK references in CREATE TABLE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_oracle_create_table_includes_fk_constraints() -> None:
    """Oracle CREATE TABLE should include FK constraints via _get_inner_statements."""
    from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor

    class Company(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=300)

        class Meta:
            table = "company"
            app = "models"

    class Employee(Model):
        id = fields.IntField(pk=True)
        company: ForeignKeyFieldInstance[Any] = fields.ForeignKeyField(
            "models.Company",
            source_field="company_id",
            related_name="employees",
        )

        class Meta:
            table = "employee"
            app = "models"

    init_apps(Company, Employee)

    client = FakeClient("oracle", inline_comment=False)
    editor = OracleSchemaEditor(client)
    await editor.create_model(Employee)

    assert len(client.executed) == 1
    assert client.executed[0] == (
        'CREATE TABLE "employee" (\n'
        '    "id" INT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY NOT NULL,\n'
        '    "company_id" INT NOT NULL,\n'
        '    CONSTRAINT "fk_employee_company_b3e5bff3" FOREIGN KEY ("company_id")'
        ' REFERENCES "company" ("id") ON DELETE CASCADE\n'
        ");"
    )


# ---------------------------------------------------------------------------
# Oracle ALTER field (MODIFY syntax)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_oracle_alter_field_null_to_not_null() -> None:
    """Oracle should use MODIFY with type for null->not-null change."""
    from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor

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

    client = FakeClient("oracle", inline_comment=False)
    editor = OracleSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "budget")

    assert len(client.executed) == 1
    assert client.executed[0] == (
        'ALTER TABLE "department" MODIFY ("budget" DECIMAL(12,2) NOT NULL)'
    )


@pytest.mark.asyncio
async def test_oracle_alter_field_not_null_to_null() -> None:
    """Oracle should use MODIFY with type for not-null->null change."""
    from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor

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

    client = FakeClient("oracle", inline_comment=False)
    editor = OracleSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "budget")

    assert len(client.executed) == 1
    assert client.executed[0] == ('ALTER TABLE "department" MODIFY ("budget" DECIMAL(12,2) NULL)')


@pytest.mark.asyncio
async def test_oracle_alter_field_set_default() -> None:
    """Oracle should use MODIFY with DEFAULT for setting a default."""
    from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField()

        class Meta:
            table = "product"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField(db_default=42)

        class Meta:
            table = "product"
            app = "models"

    client = FakeClient("oracle", inline_comment=False)
    editor = OracleSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "stock")

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "product" MODIFY ("stock" DEFAULT 42)'


@pytest.mark.asyncio
async def test_oracle_alter_field_drop_default() -> None:
    """Oracle should use MODIFY with DEFAULT NULL to drop a default."""
    from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField(db_default=42)

        class Meta:
            table = "product"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        stock = fields.IntField()

        class Meta:
            table = "product"
            app = "models"

    client = FakeClient("oracle", inline_comment=False)
    editor = OracleSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "stock")

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "product" MODIFY ("stock" DEFAULT NULL)'


# ---------------------------------------------------------------------------
# ALTER COLUMN TYPE tests (max_length changes)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_alter_field_max_length() -> None:
    """PostgreSQL alter_field changing max_length should emit ALTER COLUMN TYPE."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=32, null=True)

        class Meta:
            table = "widget"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=64, null=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" ALTER COLUMN "name" TYPE VARCHAR(64)'


@pytest.mark.asyncio
async def test_mysql_alter_field_max_length() -> None:
    """MySQL alter_field changing max_length should use MODIFY COLUMN."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=32, null=True)

        class Meta:
            table = "widget"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=64, null=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    assert len(client.executed) == 1
    assert client.executed[0] == "ALTER TABLE `widget` MODIFY COLUMN `name` VARCHAR(64) NULL"


@pytest.mark.asyncio
async def test_mssql_alter_field_max_length() -> None:
    """MSSQL alter_field changing max_length should use ALTER COLUMN with full type."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=32, null=True)

        class Meta:
            table = "widget"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=64, null=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("mssql")
    editor = MSSQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    assert len(client.executed) == 1
    assert client.executed[0] == "ALTER TABLE [widget] ALTER COLUMN [name] VARCHAR(64) NULL"


# ---------------------------------------------------------------------------
# Bug 1: MySQL MODIFY COLUMN preserves db_default (Issue #2141)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mysql_alter_field_max_length_preserves_db_default() -> None:
    """MySQL MODIFY COLUMN for max_length change must re-emit SET DEFAULT."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=10, db_default="")

        class Meta:
            table = "profile"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=20, db_default="")

        class Meta:
            table = "profile"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "MODIFY COLUMN" in sql
    assert "DEFAULT ''" in sql


@pytest.mark.asyncio
async def test_mysql_alter_field_null_change_preserves_db_default() -> None:
    """MySQL MODIFY COLUMN for null change must preserve DEFAULT in the same statement."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        value = fields.IntField(null=False, db_default=99)

        class Meta:
            table = "score"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        value = fields.IntField(null=True, db_default=99)

        class Meta:
            table = "score"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "value")

    assert len(client.executed) == 1
    sql = client.executed[0]
    assert "MODIFY COLUMN" in sql
    assert "DEFAULT 99" in sql


# ---------------------------------------------------------------------------
# Bug 2: Description changes emit real SQL (Issue #2141)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_alter_field_description_change() -> None:
    """PostgreSQL should emit COMMENT ON COLUMN when description changes."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="item name")

        class Meta:
            table = "item"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="short item name")

        class Meta:
            table = "item"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    assert len(client.executed) == 1
    assert "COMMENT ON COLUMN" in client.executed[0]
    assert "short item name" in client.executed[0]


@pytest.mark.asyncio
async def test_postgres_alter_field_description_removal() -> None:
    """PostgreSQL should emit COMMENT ON COLUMN ... IS NULL when description removed."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="item name")

        class Meta:
            table = "item"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100)

        class Meta:
            table = "item"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    assert len(client.executed) == 1
    assert "IS NULL" in client.executed[0]


@pytest.mark.asyncio
async def test_mysql_alter_field_description_change() -> None:
    """MySQL should emit MODIFY COLUMN with COMMENT when description changes."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="item name")

        class Meta:
            table = "item"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="short item name")

        class Meta:
            table = "item"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    assert len(client.executed) == 1
    assert "MODIFY COLUMN" in client.executed[0]
    assert "COMMENT" in client.executed[0]
    assert "short item name" in client.executed[0]


@pytest.mark.asyncio
async def test_base_alter_field_description_change_noop() -> None:
    """Base editor should emit no SQL for description-only changes (unsupported)."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="old desc")

        class Meta:
            table = "item"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="new desc")

        class Meta:
            table = "item"
            app = "models"

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    assert len(client.executed) == 0


# ---------------------------------------------------------------------------
# Step 3: Combined description + other changes on MySQL (Issue #2141)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mysql_alter_field_null_and_description_combined() -> None:
    """MySQL should emit a single MODIFY COLUMN with both NULL and COMMENT."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="old desc")

        class Meta:
            table = "item"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, null=True, description="new desc")

        class Meta:
            table = "item"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    # Should be a single MODIFY COLUMN with both NULL and COMMENT
    modify_stmts = [s for s in client.executed if "MODIFY COLUMN" in s]
    assert len(modify_stmts) == 1
    assert "NULL" in modify_stmts[0]
    assert "COMMENT" in modify_stmts[0]
    assert "new desc" in modify_stmts[0]


@pytest.mark.asyncio
async def test_mysql_alter_field_null_change_preserves_description() -> None:
    """MySQL MODIFY COLUMN for null change must preserve existing COMMENT."""

    class OldWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, description="keep this")

        class Meta:
            table = "item"
            app = "models"

    class NewWidget(Model):
        id = fields.IntField(pk=True)
        name = fields.CharField(max_length=100, null=True, description="keep this")

        class Meta:
            table = "item"
            app = "models"

    client = FakeClient("mysql")
    editor = MySQLSchemaEditor(client)
    await editor.alter_field(OldWidget, NewWidget, "name")

    modify_stmts = [s for s in client.executed if "MODIFY COLUMN" in s]
    assert len(modify_stmts) == 1
    assert "COMMENT" in modify_stmts[0]
    assert "keep this" in modify_stmts[0]
