"""Tests for introspection-based unique constraint removal across all backends."""

from __future__ import annotations

import pytest

from tests.utils.fake_client import FakeClient, MockIntrospectionClient
from tortoise import fields
from tortoise.migrations.constraints import CheckConstraint, UniqueConstraint
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
from tortoise.migrations.schema_editor.mssql import MSSQLSchemaEditor
from tortoise.migrations.schema_editor.mysql import MySQLSchemaEditor
from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor
from tortoise.migrations.schema_editor.sqlite import SqliteSchemaEditor
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
# FK test models (used by FK resolution tests)
# ---------------------------------------------------------------------------


class Organization(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)

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


init_apps(Organization, Membership)


# Each backend's introspection returns a different dict key for the constraint name.
# SQLite uses PRAGMA-based introspection (tested separately below).
#
# Fields: editor_cls, client_kwargs, mock_row, expected_name,
#         expected_drop_sql (introspected name), expected_fallback_sql (uid_ name)
INTROSPECTION_BACKENDS = [
    pytest.param(
        BasePostgresSchemaEditor,
        {"dialect": "postgres", "inline_comment": False},
        {"conname": "legacy_auto_name"},
        "legacy_auto_name",
        'ALTER TABLE "widget" DROP CONSTRAINT "legacy_auto_name"',
        'ALTER TABLE "widget" DROP CONSTRAINT "uid_widget_email_3d71d7"',
        id="postgres",
    ),
    pytest.param(
        MySQLSchemaEditor,
        {"dialect": "mysql"},
        {"CONSTRAINT_NAME": "old_auto_name"},
        "old_auto_name",
        "DROP INDEX `old_auto_name` ON `widget`",
        "DROP INDEX `uid_widget_email_3d71d7` ON `widget`",
        id="mysql",
    ),
    pytest.param(
        MSSQLSchemaEditor,
        {"dialect": "mssql", "inline_comment": False},
        {"name": "UQ__widget__email_legacy"},
        "UQ__widget__email_legacy",
        "ALTER TABLE [widget] DROP CONSTRAINT [UQ__widget__email_legacy]",
        "ALTER TABLE [widget] DROP CONSTRAINT [uid_widget_email_3d71d7]",
        id="mssql",
    ),
    pytest.param(
        OracleSchemaEditor,
        {"dialect": "oracle", "inline_comment": False},
        {"CONSTRAINT_NAME": "SYS_C0012345"},
        "SYS_C0012345",
        'ALTER TABLE "widget" DROP CONSTRAINT "SYS_C0012345"',
        'ALTER TABLE "widget" DROP CONSTRAINT "uid_widget_email_3d71d7"',
        id="oracle",
    ),
]


@pytest.mark.asyncio
async def test_base_get_unique_constraint_names_from_db_returns_empty() -> None:
    """Base _get_unique_constraint_names_from_db returns [] (no introspection)."""
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    result = await editor._get_unique_constraint_names_from_db("widget", ["name"], None)
    assert result == []
    assert len(client.executed) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "mock_row", "expected_name", "_drop", "_fallback"),
    INTROSPECTION_BACKENDS,
)
async def test_introspection_returns_constraint_names(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    mock_row: dict,
    expected_name: str,
    _drop: str,
    _fallback: str,
) -> None:
    """Backend introspection returns the constraint name from mock results."""
    client = MockIntrospectionClient(constraint_names=[mock_row], **client_kwargs)
    editor = editor_cls(client)
    result = await editor._get_unique_constraint_names_from_db("widget", ["email"], None)
    assert result == [expected_name]
    assert len(client.executed) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "mock_row", "expected_name", "expected_drop_sql", "_fallback"),
    INTROSPECTION_BACKENDS,
)
async def test_remove_constraint_uses_introspected_name(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    mock_row: dict,
    expected_name: str,
    expected_drop_sql: str,
    _fallback: str,
) -> None:
    """remove_constraint should use the introspected name instead of uid_."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255, unique=True)

        class Meta:
            table = "widget"
            app = "models"

    client = MockIntrospectionClient(constraint_names=[mock_row], **client_kwargs)
    editor = editor_cls(client)

    constraint = UniqueConstraint(fields=("email",))
    await editor.remove_constraint(Widget, constraint)

    assert len(client.executed) == 1
    assert client.executed[0] == expected_drop_sql


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "editor_cls",
        "client_kwargs",
        "_mock_row",
        "_expected_name",
        "_drop",
        "expected_fallback_sql",
    ),
    INTROSPECTION_BACKENDS,
)
async def test_remove_constraint_fallback_with_fakeclient(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    _mock_row: dict,
    _expected_name: str,
    _drop: str,
    expected_fallback_sql: str,
) -> None:
    """With FakeClient (no introspection) falls back to deterministic uid_ name."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255, unique=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient(**client_kwargs)
    editor = editor_cls(client)

    constraint = UniqueConstraint(fields=("email",))
    await editor.remove_constraint(Widget, constraint)

    assert len(client.executed) == 1
    assert client.executed[0] == expected_fallback_sql


# ---------------------------------------------------------------------------
# SQLite-specific introspection tests (PRAGMA-based, different mock shape)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sqlite_introspection_raises_with_fakeclient() -> None:
    """SQLite _get_unique_constraint_names_from_db raises when FakeClient has no execute_query."""
    client = FakeClient("sqlite")
    editor = SqliteSchemaEditor(client)
    with pytest.raises(NotImplementedError):
        await editor._get_unique_constraint_names_from_db("widget", ["name"], None)
    assert len(client.executed) == 0


@pytest.mark.asyncio
async def test_sqlite_introspection_finds_unique_index() -> None:
    """SQLite introspection should find unique index by column using PRAGMA."""
    client = MockIntrospectionClient(
        "sqlite",
        pragma_index_list=[
            {
                "seq": 0,
                "name": "sqlite_autoindex_widget_1",
                "unique": 1,
                "origin": "c",
                "partial": 0,
            },
        ],
        pragma_index_info={
            "sqlite_autoindex_widget_1": [{"seqno": 0, "cid": 1, "name": "email"}],
        },
    )
    editor = SqliteSchemaEditor(client)
    result = await editor._get_unique_constraint_names_from_db("widget", ["email"], None)
    assert result == ["sqlite_autoindex_widget_1"]
    assert len(client.executed) == 0


@pytest.mark.asyncio
async def test_sqlite_remove_constraint_fallback_with_fakeclient() -> None:
    """SQLite with FakeClient falls back to deterministic uid_ name."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255, unique=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("sqlite")
    editor = SqliteSchemaEditor(client)

    constraint = UniqueConstraint(fields=("email",))
    await editor.remove_constraint(Widget, constraint)

    assert len(client.executed) == 1
    assert client.executed[0] == 'DROP INDEX "uid_widget_email_3d71d7"'


# ---------------------------------------------------------------------------
# FK field-to-column resolution tests
# ---------------------------------------------------------------------------

ADD_CONSTRAINT_BACKENDS = [
    pytest.param(
        TestSchemaEditor,
        {"dialect": "sql"},
        'ALTER TABLE "membership" ADD CONSTRAINT "uid_membership_organiz_04ef0e" UNIQUE ("organization_id", "user_email")',
        id="base",
    ),
    pytest.param(
        BasePostgresSchemaEditor,
        {"dialect": "postgres", "inline_comment": False},
        'ALTER TABLE "membership" ADD CONSTRAINT "uid_membership_organiz_04ef0e" UNIQUE ("organization_id", "user_email")',
        id="postgres",
    ),
    pytest.param(
        MySQLSchemaEditor,
        {"dialect": "mysql"},
        "ALTER TABLE `membership` ADD UNIQUE KEY `uidx_membership_organiz_04ef0e` (`organization_id`, `user_email`)",
        id="mysql",
    ),
    pytest.param(
        SqliteSchemaEditor,
        {"dialect": "sqlite"},
        'CREATE UNIQUE INDEX "uid_membership_organiz_04ef0e" ON "membership" ("organization_id", "user_email");',
        id="sqlite",
    ),
    pytest.param(
        MSSQLSchemaEditor,
        {"dialect": "mssql", "inline_comment": False},
        "ALTER TABLE [membership] ADD CONSTRAINT [uid_membership_organiz_04ef0e] UNIQUE ([organization_id], [user_email])",
        id="mssql",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "expected_sql"),
    ADD_CONSTRAINT_BACKENDS,
)
async def test_add_constraint_resolves_fk_fields(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    expected_sql: str,
) -> None:
    """add_constraint with FK field name must resolve to DB column name (organization_id)."""
    client = FakeClient(**client_kwargs)
    editor = editor_cls(client)

    constraint = UniqueConstraint(fields=("organization", "user_email"))
    await editor.add_constraint(Membership, constraint)

    assert len(client.executed) == 1
    assert client.executed[0] == expected_sql


@pytest.mark.asyncio
async def test_add_constraint_idempotent_for_resolved_names() -> None:
    """add_constraint with already-resolved DB column names (organization_id) works correctly."""
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    constraint = UniqueConstraint(fields=("organization_id", "user_email"))
    await editor.add_constraint(Membership, constraint)

    assert len(client.executed) == 1
    assert (
        client.executed[0]
        == 'ALTER TABLE "membership" ADD CONSTRAINT "uid_membership_organiz_04ef0e" UNIQUE ("organization_id", "user_email")'
    )


REMOVE_CONSTRAINT_FK_BACKENDS = [
    pytest.param(
        BasePostgresSchemaEditor,
        {"dialect": "postgres", "inline_comment": False},
        {"conname": "test_constraint"},
        ['ALTER TABLE "membership" DROP CONSTRAINT "test_constraint"'],
        id="postgres",
    ),
    pytest.param(
        MySQLSchemaEditor,
        {"dialect": "mysql"},
        {"CONSTRAINT_NAME": "test_constraint"},
        [
            "CREATE INDEX `fkidx_membership_organiz_ae9a44` ON `membership` (`organization_id`);",
            "DROP INDEX `test_constraint` ON `membership`",
        ],
        id="mysql",
    ),
    pytest.param(
        MSSQLSchemaEditor,
        {"dialect": "mssql", "inline_comment": False},
        {"name": "test_constraint"},
        ["ALTER TABLE [membership] DROP CONSTRAINT [test_constraint]"],
        id="mssql",
    ),
    pytest.param(
        OracleSchemaEditor,
        {"dialect": "oracle", "inline_comment": False},
        {"CONSTRAINT_NAME": "test_constraint"},
        ['ALTER TABLE "membership" DROP CONSTRAINT "test_constraint"'],
        id="oracle",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "mock_row", "expected_sqls"),
    REMOVE_CONSTRAINT_FK_BACKENDS,
)
async def test_remove_constraint_resolves_fk_for_introspection(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    mock_row: dict,
    expected_sqls: list[str],
) -> None:
    """remove_constraint with FK field name resolves to DB column for introspection query."""
    client = MockIntrospectionClient(constraint_names=[mock_row], **client_kwargs)
    editor = editor_cls(client)

    constraint = UniqueConstraint(fields=("organization", "user_email"))
    await editor.remove_constraint(Membership, constraint)

    assert len(client.executed) == len(expected_sqls)
    assert client.executed == expected_sqls


@pytest.mark.asyncio
async def test_rename_constraint_resolves_fk_fields() -> None:
    """rename_constraint on FK model uses resolved column names."""
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    old_constraint = UniqueConstraint(fields=("organization", "user_email"), name="old_name")
    new_constraint = UniqueConstraint(fields=("organization", "user_email"), name="new_name")
    await editor.rename_constraint(Membership, old_constraint, new_constraint)

    assert len(client.executed) == 1
    assert (
        client.executed[0] == 'ALTER TABLE "membership" RENAME CONSTRAINT "old_name" TO "new_name"'
    )


# ---------------------------------------------------------------------------
# CheckConstraint tests
# ---------------------------------------------------------------------------

CHECK_CONSTRAINT_BACKENDS = [
    pytest.param(
        TestSchemaEditor,
        {"dialect": "sql"},
        'ALTER TABLE "product" ADD CONSTRAINT "ck_price" CHECK (price > 0)',
        id="base",
    ),
    pytest.param(
        BasePostgresSchemaEditor,
        {"dialect": "postgres", "inline_comment": False},
        'ALTER TABLE "product" ADD CONSTRAINT "ck_price" CHECK (price > 0)',
        id="postgres",
    ),
    pytest.param(
        MySQLSchemaEditor,
        {"dialect": "mysql"},
        "ALTER TABLE `product` ADD CONSTRAINT `ck_price` CHECK (price > 0)",
        id="mysql",
    ),
    pytest.param(
        MSSQLSchemaEditor,
        {"dialect": "mssql", "inline_comment": False},
        "ALTER TABLE [product] ADD CONSTRAINT [ck_price] CHECK (price > 0)",
        id="mssql",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "expected_sql"),
    CHECK_CONSTRAINT_BACKENDS,
)
async def test_add_check_constraint_generates_sql(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    expected_sql: str,
) -> None:
    """add_constraint with CheckConstraint generates correct SQL per backend."""

    class Product(Model):
        id = fields.IntField(pk=True)
        price = fields.DecimalField(max_digits=10, decimal_places=2)

        class Meta:
            table = "product"
            app = "models"

    client = FakeClient(**client_kwargs)
    editor = editor_cls(client)

    constraint = CheckConstraint(check="price > 0", name="ck_price")
    await editor.add_constraint(Product, constraint)

    assert len(client.executed) == 1
    assert client.executed[0] == expected_sql


@pytest.mark.asyncio
async def test_remove_check_constraint_generates_sql() -> None:
    """remove_constraint with CheckConstraint generates DROP CONSTRAINT SQL."""

    class Product(Model):
        id = fields.IntField(pk=True)
        price = fields.DecimalField(max_digits=10, decimal_places=2)

        class Meta:
            table = "product"
            app = "models"

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    constraint = CheckConstraint(check="price > 0", name="ck_price")
    await editor.remove_constraint(Product, constraint)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "product" DROP CONSTRAINT "ck_price"'


@pytest.mark.asyncio
async def test_sqlite_add_check_constraint_rebuilds_table() -> None:
    """SQLite adds CHECK constraints by rebuilding the table."""

    class Product(Model):
        id = fields.IntField(pk=True)
        price = fields.DecimalField(max_digits=10, decimal_places=2)

        class Meta:
            table = "product"
            app = "models"
            constraints = [CheckConstraint(check="price > 0", name="ck_price")]

    client = FakeClient("sqlite")
    editor = SqliteSchemaEditor(client)

    constraint = CheckConstraint(check="price > 0", name="ck_price")
    await editor.add_constraint(Product, constraint)

    assert len(client.executed) == 4
    assert client.executed[0] == (
        'CREATE TABLE "new__product" ('
        '"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, '
        '"price" VARCHAR(40) NOT NULL, '
        'CONSTRAINT "ck_price" CHECK (price > 0))'
    )
    assert client.executed[1] == (
        'INSERT INTO "new__product" ("id", "price")\n'
        '                SELECT "id", "price"\n'
        '                FROM "product"'
    )
    assert client.executed[2] == 'DROP TABLE "product"'
    assert client.executed[3] == 'ALTER TABLE "new__product" RENAME TO "product"'


# ---------------------------------------------------------------------------
# Partial unique index (condition) tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_add_constraint_with_condition_generates_partial_index() -> None:
    """PostgreSQL generates CREATE UNIQUE INDEX ... WHERE for partial unique constraints."""

    class UserAccount(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255)
        is_active = fields.BooleanField(default=True)

        class Meta:
            table = "user_account"
            app = "models"

    client = FakeClient("postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)

    constraint = UniqueConstraint(
        fields=("email",), name="uq_active_email", condition="is_active = true"
    )
    await editor.add_constraint(UserAccount, constraint)

    assert len(client.executed) == 1
    assert (
        client.executed[0]
        == 'CREATE UNIQUE INDEX "uq_active_email" ON "user_account" ("email") WHERE is_active = true;'
    )


@pytest.mark.asyncio
async def test_base_add_constraint_with_condition_raises() -> None:
    """Non-PostgreSQL backends raise NotImplementedError for partial unique constraints."""

    class UserAccount(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255)
        is_active = fields.BooleanField(default=True)

        class Meta:
            table = "user_account"
            app = "models"

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    constraint = UniqueConstraint(
        fields=("email",), name="uq_active_email", condition="is_active = true"
    )
    with pytest.raises(NotImplementedError, match="Partial unique indexes"):
        await editor.add_constraint(UserAccount, constraint)
    assert len(client.executed) == 0
