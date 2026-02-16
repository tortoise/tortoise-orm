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
INTROSPECTION_BACKENDS = [
    pytest.param(
        BasePostgresSchemaEditor,
        {"dialect": "postgres", "inline_comment": False},
        {"conname": "legacy_auto_name"},
        "legacy_auto_name",
        id="postgres",
    ),
    pytest.param(
        MySQLSchemaEditor,
        {"dialect": "mysql"},
        {"CONSTRAINT_NAME": "old_auto_name"},
        "old_auto_name",
        id="mysql",
    ),
    pytest.param(
        MSSQLSchemaEditor,
        {"dialect": "mssql", "inline_comment": False},
        {"name": "UQ__widget__email_legacy"},
        "UQ__widget__email_legacy",
        id="mssql",
    ),
    pytest.param(
        OracleSchemaEditor,
        {"dialect": "oracle", "inline_comment": False},
        {"CONSTRAINT_NAME": "SYS_C0012345"},
        "SYS_C0012345",
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "mock_row", "expected_name"),
    INTROSPECTION_BACKENDS,
)
async def test_introspection_returns_constraint_names(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    mock_row: dict,
    expected_name: str,
) -> None:
    """Backend introspection returns the constraint name from mock results."""
    client = MockIntrospectionClient(constraint_names=[mock_row], **client_kwargs)
    editor = editor_cls(client)
    result = await editor._get_unique_constraint_names_from_db("widget", ["email"], None)
    assert result == [expected_name]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "mock_row", "expected_name"),
    INTROSPECTION_BACKENDS,
)
async def test_remove_constraint_uses_introspected_name(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    mock_row: dict,
    expected_name: str,
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

    assert client.executed
    drop_sql = client.executed[0]
    assert expected_name in drop_sql
    assert "uid_" not in drop_sql


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "mock_row", "expected_name"),
    INTROSPECTION_BACKENDS,
)
async def test_remove_constraint_fallback_with_fakeclient(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    mock_row: dict,
    expected_name: str,
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

    assert client.executed
    drop_sql = client.executed[0]
    assert "uid_" in drop_sql


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

    assert client.executed
    drop_sql = client.executed[0]
    assert '"uid_' in drop_sql


# ---------------------------------------------------------------------------
# FK field-to-column resolution tests
# ---------------------------------------------------------------------------

ADD_CONSTRAINT_BACKENDS = [
    pytest.param(
        TestSchemaEditor,
        {"dialect": "sql"},
        "organization_id",
        "user_email",
        id="base",
    ),
    pytest.param(
        BasePostgresSchemaEditor,
        {"dialect": "postgres", "inline_comment": False},
        "organization_id",
        "user_email",
        id="postgres",
    ),
    pytest.param(
        MySQLSchemaEditor,
        {"dialect": "mysql"},
        "organization_id",
        "user_email",
        id="mysql",
    ),
    pytest.param(
        SqliteSchemaEditor,
        {"dialect": "sqlite"},
        "organization_id",
        "user_email",
        id="sqlite",
    ),
    pytest.param(
        MSSQLSchemaEditor,
        {"dialect": "mssql", "inline_comment": False},
        "organization_id",
        "user_email",
        id="mssql",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "expected_fk_col", "expected_regular_col"),
    ADD_CONSTRAINT_BACKENDS,
)
async def test_add_constraint_resolves_fk_fields(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    expected_fk_col: str,
    expected_regular_col: str,
) -> None:
    """add_constraint with FK field name must resolve to DB column name (organization_id)."""
    client = FakeClient(**client_kwargs)
    editor = editor_cls(client)

    constraint = UniqueConstraint(fields=("organization", "user_email"))
    await editor.add_constraint(Membership, constraint)

    assert client.executed
    sql = client.executed[0]
    assert expected_fk_col in sql, f"Expected '{expected_fk_col}' in SQL: {sql}"
    assert expected_regular_col in sql, f"Expected '{expected_regular_col}' in SQL: {sql}"
    # Must NOT contain the raw model field name 'organization' as a quoted column
    assert (
        '"organization"' not in sql and "`organization`" not in sql and "[organization]" not in sql
    ), f"SQL should not contain raw model field name 'organization': {sql}"


@pytest.mark.asyncio
async def test_add_constraint_idempotent_for_resolved_names() -> None:
    """add_constraint with already-resolved DB column names (organization_id) works correctly."""
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    constraint = UniqueConstraint(fields=("organization_id", "user_email"))
    await editor.add_constraint(Membership, constraint)

    assert client.executed
    sql = client.executed[0]
    assert "organization_id" in sql
    assert "user_email" in sql


REMOVE_CONSTRAINT_FK_BACKENDS = [
    pytest.param(
        BasePostgresSchemaEditor,
        {"dialect": "postgres", "inline_comment": False},
        {"conname": "test_constraint"},
        id="postgres",
    ),
    pytest.param(
        MySQLSchemaEditor,
        {"dialect": "mysql"},
        {"CONSTRAINT_NAME": "test_constraint"},
        id="mysql",
    ),
    pytest.param(
        MSSQLSchemaEditor,
        {"dialect": "mssql", "inline_comment": False},
        {"name": "test_constraint"},
        id="mssql",
    ),
    pytest.param(
        OracleSchemaEditor,
        {"dialect": "oracle", "inline_comment": False},
        {"CONSTRAINT_NAME": "test_constraint"},
        id="oracle",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "mock_row"),
    REMOVE_CONSTRAINT_FK_BACKENDS,
)
async def test_remove_constraint_resolves_fk_for_introspection(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    mock_row: dict,
) -> None:
    """remove_constraint with FK field name resolves to DB column for introspection query."""
    client = MockIntrospectionClient(constraint_names=[mock_row], **client_kwargs)
    editor = editor_cls(client)

    constraint = UniqueConstraint(fields=("organization", "user_email"))
    await editor.remove_constraint(Membership, constraint)

    assert client.executed
    drop_sql = client.executed[-1]
    assert "test_constraint" in drop_sql


@pytest.mark.asyncio
async def test_rename_constraint_resolves_fk_fields() -> None:
    """rename_constraint on FK model uses resolved column names."""
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    old_constraint = UniqueConstraint(fields=("organization", "user_email"), name="old_name")
    new_constraint = UniqueConstraint(fields=("organization", "user_email"), name="new_name")
    await editor.rename_constraint(Membership, old_constraint, new_constraint)

    assert client.executed
    sql = client.executed[0]
    assert "old_name" in sql
    assert "new_name" in sql


# ---------------------------------------------------------------------------
# CheckConstraint tests
# ---------------------------------------------------------------------------

CHECK_CONSTRAINT_BACKENDS = [
    pytest.param(
        TestSchemaEditor,
        {"dialect": "sql"},
        'CONSTRAINT "ck_price" CHECK (price > 0)',
        id="base",
    ),
    pytest.param(
        BasePostgresSchemaEditor,
        {"dialect": "postgres", "inline_comment": False},
        'CONSTRAINT "ck_price" CHECK (price > 0)',
        id="postgres",
    ),
    pytest.param(
        MySQLSchemaEditor,
        {"dialect": "mysql"},
        "CONSTRAINT `ck_price` CHECK (price > 0)",
        id="mysql",
    ),
    pytest.param(
        MSSQLSchemaEditor,
        {"dialect": "mssql", "inline_comment": False},
        "CONSTRAINT [ck_price] CHECK (price > 0)",
        id="mssql",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "expected_fragment"),
    CHECK_CONSTRAINT_BACKENDS,
)
async def test_add_check_constraint_generates_sql(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    expected_fragment: str,
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

    assert client.executed
    sql = client.executed[0]
    assert expected_fragment in sql, f"Expected '{expected_fragment}' in SQL: {sql}"


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

    assert client.executed
    sql = client.executed[0]
    assert 'DROP CONSTRAINT "ck_price"' in sql


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

    assert client.executed
    create_sql = client.executed[0]
    assert "new__product" in create_sql, f"Expected table rebuild in SQL: {create_sql}"
    assert "CHECK (price > 0)" in create_sql, f"Expected CHECK constraint in SQL: {create_sql}"


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

    assert client.executed
    sql = client.executed[0]
    assert 'CREATE UNIQUE INDEX "uq_active_email"' in sql
    assert "WHERE is_active = true" in sql


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
