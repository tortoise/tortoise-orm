"""Tests for introspection-based unique constraint removal across all backends."""

from __future__ import annotations

import pytest

from tests.utils.fake_client import FakeClient, MockIntrospectionClient
from tortoise import fields
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
from tortoise.migrations.schema_editor.mssql import MSSQLSchemaEditor
from tortoise.migrations.schema_editor.mysql import MySQLSchemaEditor
from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor
from tortoise.migrations.schema_editor.sqlite import SqliteSchemaEditor
from tortoise.models import Model


class TestSchemaEditor(BaseSchemaEditor):
    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return ""

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return ""


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
    result = await editor._get_unique_constraint_names_from_db("widget", "name", None)
    assert result == []


@pytest.mark.asyncio
async def test_base_remove_constraint_fallback_to_deterministic_name() -> None:
    """When introspection returns empty, remove_constraint uses deterministic uid_ name."""

    class WidgetEmail(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255, unique=True)

        class Meta:
            table = "widget"
            app = "models"

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    constraint = UniqueConstraint(fields=("email",))
    await editor.remove_constraint(WidgetEmail, constraint)

    assert client.executed
    drop_sql = client.executed[0]
    assert 'DROP CONSTRAINT "uid_' in drop_sql


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
    result = await editor._get_unique_constraint_names_from_db("widget", "email", None)
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("editor_cls", "client_kwargs", "mock_row", "expected_name"),
    INTROSPECTION_BACKENDS,
)
async def test_empty_introspection_falls_back_to_deterministic_name(
    editor_cls: type[BaseSchemaEditor],
    client_kwargs: dict,
    mock_row: dict,
    expected_name: str,
) -> None:
    """When introspection returns empty list, use deterministic uid_ name."""

    class Widget(Model):
        id = fields.IntField(pk=True)
        email = fields.CharField(max_length=255, unique=True)

        class Meta:
            table = "widget"
            app = "models"

    client = MockIntrospectionClient(constraint_names=[], **client_kwargs)
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
        await editor._get_unique_constraint_names_from_db("widget", "name", None)


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
    result = await editor._get_unique_constraint_names_from_db("widget", "email", None)
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
