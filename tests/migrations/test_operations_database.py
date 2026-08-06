from __future__ import annotations

from typing import Any

import pytest

from tests.utils.fake_client import FakeClient, MockIntrospectionClient
from tortoise import fields
from tortoise.fields.base import Field
from tortoise.indexes import Index
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.exceptions import IncompatibleStateError
from tortoise.migrations.operations import (
    AddConstraint,
    AddField,
    AddIndex,
    AlterField,
    CreateModel,
    DeleteModel,
    RemoveField,
    RemoveIndex,
    RenameConstraint,
    RenameIndex,
    RenameModel,
    RunPython,
    RunSQL,
)
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
from tortoise.migrations.schema_editor.mysql import MySQLSchemaEditor
from tortoise.migrations.schema_generator.state import ModelState, State
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


class TestSchemaEditor(BaseSchemaEditor):
    def _get_table_comment_sql(self, table: str, comment: str) -> str:
        return ""

    def _get_column_comment_sql(self, table: str, column: str, comment: str) -> str:
        return ""


def make_model(
    model_name: str,
    *,
    meta_options: dict[str, Any] | None = None,
    **model_fields: Field,
) -> type[Model]:
    attrs: dict[str, Any] = dict(model_fields)
    options: dict[str, Any] = {"app": "models", "table": "widget"}
    if meta_options:
        options.update(meta_options)
    attrs["Meta"] = type("Meta", (), options)
    return type(model_name, (Model,), attrs)


def build_state(app_label: str, model: type) -> State:
    apps = StateApps()
    state = State(models={}, apps=apps)
    model_state = ModelState.make_from_model(app_label, model)
    state.models[(app_label, model.__name__)] = model_state
    model_clone = model_state.render(apps)
    apps.register_model(app_label, model_clone)
    return state


@pytest.mark.asyncio
async def test_create_model_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())

    op = CreateModel(
        name="Widget",
        fields=[("id", fields.IntField(pk=True)), ("name", fields.TextField())],
    )

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == (
        'CREATE TABLE "widget" (\n    "id" INT NOT NULL  PRIMARY KEY,\n    "name" TEXT NOT NULL\n);'
    )


@pytest.mark.asyncio
async def test_add_field_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = AddField(model_name="Widget", name="name", field=fields.TextField())

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" ADD COLUMN "name" TEXT NOT NULL'


@pytest.mark.asyncio
async def test_delete_model_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = DeleteModel(name="Widget")

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'DROP TABLE "widget" CASCADE'


@pytest.mark.asyncio
async def test_add_index_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = AddIndex(
        model_name="Widget",
        index=Index(fields=("id",), name="idx_widget_id"),
    )

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'CREATE INDEX "idx_widget_id" ON "widget" ("id");'


@pytest.mark.asyncio
async def test_remove_index_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )
    AddIndex(
        model_name="Widget",
        index=Index(fields=("id",), name="idx_widget_id"),
    ).state_forward("models", state)

    op = RemoveIndex(model_name="Widget", name="idx_widget_id")

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'DROP INDEX "idx_widget_id"'


@pytest.mark.asyncio
async def test_rename_index_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )
    AddIndex(
        model_name="Widget",
        index=Index(fields=("id",), name="idx_widget_id"),
    ).state_forward("models", state)

    op = RenameIndex(model_name="Widget", old_name="idx_widget_id", new_name="idx_widget_id_new")

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER INDEX "idx_widget_id" RENAME TO "idx_widget_id_new"'


@pytest.mark.asyncio
async def test_add_constraint_operation_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = AddConstraint(
        model_name="Widget",
        constraint=UniqueConstraint(fields=("id",), name="uniq_widget_id"),
    )

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert (
        client.executed[0] == 'ALTER TABLE "widget" ADD CONSTRAINT "uniq_widget_id" UNIQUE ("id")'
    )


@pytest.mark.asyncio
async def test_alter_field_backward_renames_columns() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)

    OldWidget = make_model(
        "Widget",
        id=fields.IntField(pk=True),
        body=fields.TextField(),
    )
    NewWidget = make_model(
        "Widget",
        id=fields.IntField(pk=True),
        body=fields.TextField(source_field="content"),
    )

    old_state = build_state("models", NewWidget)
    new_state = build_state("models", OldWidget)

    op = AlterField(model_name="Widget", name="body", field=fields.TextField())

    await op.database_backward("models", old_state, new_state, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" RENAME COLUMN "content" TO "body"'


@pytest.mark.asyncio
async def test_run_python_operation_runs_callable() -> None:
    calls: list[tuple[StateApps, BaseSchemaEditor]] = []
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    model = make_model("Widget", id=fields.IntField(pk=True))
    state = build_state("models", model)

    def forward(apps: StateApps, schema_editor: BaseSchemaEditor) -> None:
        apps.get_model("models.Widget")
        calls.append((apps, schema_editor))

    op = RunPython(forward)

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 0
    assert len(calls) == 1
    apps, schema_editor = calls[0]
    assert schema_editor is editor
    apps.get_model("models.Widget")


@pytest.mark.asyncio
async def test_rename_constraint_backward_runs_sql() -> None:
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    model = make_model("Widget", id=fields.IntField(pk=True))
    state = build_state("models", model)

    op = RenameConstraint(model_name="Widget", old_name="uniq_old", new_name="uniq_new")

    await op.database_backward("models", state, state, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" RENAME CONSTRAINT "uniq_new" TO "uniq_old"'


@pytest.mark.asyncio
async def test_create_model_uses_inline_unique() -> None:
    """CREATE TABLE should use inline UNIQUE for unique fields."""
    OldModel = make_model(
        "CryptoWallet",
        meta_options={"table": "crypto_wallets"},
        id=fields.IntField(pk=True),
        wallet_address=fields.CharField(max_length=255, unique=True, index=True),
    )

    create_client = FakeClient("sql")
    create_editor = TestSchemaEditor(create_client)
    await create_editor.create_model(OldModel)

    assert len(create_client.executed) == 1
    assert create_client.executed[0] == (
        'CREATE TABLE "crypto_wallets" (\n'
        '    "id" INT NOT NULL  PRIMARY KEY,\n'
        '    "wallet_address" VARCHAR(255) NOT NULL UNIQUE\n'
        ");\n"
        'CREATE INDEX "idx_crypto_wall_wallet__06570f" ON "crypto_wallets" ("wallet_address");'
    )


@pytest.mark.asyncio
async def test_alter_field_unique_to_nonunique_generates_drop_constraint() -> None:
    """Changing unique=True to unique=False should produce a DROP CONSTRAINT."""
    OldModel = make_model(
        "CryptoWallet",
        meta_options={"table": "crypto_wallets"},
        id=fields.IntField(pk=True),
        wallet_address=fields.CharField(max_length=255, unique=True, index=True),
    )
    NewModel = make_model(
        "CryptoWallet",
        meta_options={"table": "crypto_wallets"},
        id=fields.IntField(pk=True),
        wallet_address=fields.CharField(max_length=255, unique=False, index=True),
    )

    old_state = build_state("models", OldModel)
    new_state = build_state("models", NewModel)

    alter_client = FakeClient("sql")
    alter_editor = TestSchemaEditor(alter_client)
    op = AlterField(
        model_name="CryptoWallet",
        name="wallet_address",
        field=fields.CharField(max_length=255, index=True),
    )
    await op.database_forward("models", old_state, new_state, state_editor=alter_editor)

    assert len(alter_client.executed) == 1
    assert alter_client.executed[0] == (
        'ALTER TABLE "crypto_wallets" DROP CONSTRAINT "uid_crypto_wall_wallet__06570f"'
    )


# ---------------------------------------------------------------------------
# Integration tests: AlterField with introspection-based constraint removal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_alter_field_uses_introspected_legacy_name() -> None:
    """PostgreSQL AlterField unique=True->False should use the introspected constraint name."""
    OldModel = make_model(
        "CryptoWallet",
        meta_options={"table": "crypto_wallets"},
        id=fields.IntField(pk=True),
        wallet_address=fields.CharField(max_length=255, unique=True, index=True),
    )
    NewModel = make_model(
        "CryptoWallet",
        meta_options={"table": "crypto_wallets"},
        id=fields.IntField(pk=True),
        wallet_address=fields.CharField(max_length=255, unique=False, index=True),
    )

    old_state = build_state("models", OldModel)
    new_state = build_state("models", NewModel)

    client = MockIntrospectionClient(
        "postgres",
        constraint_names=[{"conname": "crypto_wallets_wallet_address_key"}],
        inline_comment=False,
    )
    editor = BasePostgresSchemaEditor(client)
    op = AlterField(
        model_name="CryptoWallet",
        name="wallet_address",
        field=fields.CharField(max_length=255, index=True),
    )
    await op.database_forward("models", old_state, new_state, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == (
        'ALTER TABLE "crypto_wallets" DROP CONSTRAINT "crypto_wallets_wallet_address_key"'
    )


@pytest.mark.asyncio
async def test_mysql_alter_field_uses_introspected_legacy_name() -> None:
    """MySQL AlterField unique=True->False should use the introspected index name."""
    OldModel = make_model(
        "CryptoWallet",
        meta_options={"table": "crypto_wallets"},
        id=fields.IntField(pk=True),
        wallet_address=fields.CharField(max_length=255, unique=True, index=True),
    )
    NewModel = make_model(
        "CryptoWallet",
        meta_options={"table": "crypto_wallets"},
        id=fields.IntField(pk=True),
        wallet_address=fields.CharField(max_length=255, unique=False, index=True),
    )

    old_state = build_state("models", OldModel)
    new_state = build_state("models", NewModel)

    client = MockIntrospectionClient(
        "mysql",
        constraint_names=[{"CONSTRAINT_NAME": "wallet_address"}],
    )
    editor = MySQLSchemaEditor(client)
    op = AlterField(
        model_name="CryptoWallet",
        name="wallet_address",
        field=fields.CharField(max_length=255, index=True),
    )
    await op.database_forward("models", old_state, new_state, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == "DROP INDEX `wallet_address` ON `crypto_wallets`"


def test_remove_field_error_message_includes_field_name() -> None:
    """RemoveField.state_forward() error should include the missing field name."""
    state = State(models={}, apps=StateApps())
    CreateModel(name="Widget", fields=[("id", fields.IntField(pk=True))]).state_forward(
        "models", state
    )

    op = RemoveField(model_name="Widget", name="nonexistent_field")

    with pytest.raises(IncompatibleStateError, match="nonexistent_field"):
        op.state_forward("models", state)


# ---------------------------------------------------------------------------
# Step 8: Mock-based SQL verification tests for uncovered operations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_field_generates_sql() -> None:
    """RemoveField should generate ALTER TABLE ... DROP COLUMN SQL."""
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(
        name="Widget",
        fields=[("id", fields.IntField(pk=True)), ("name", fields.TextField())],
    ).state_forward("models", state)

    op = RemoveField(model_name="Widget", name="name")

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" DROP COLUMN "name" CASCADE'


@pytest.mark.asyncio
async def test_rename_model_generates_sql() -> None:
    """RenameModel should generate ALTER TABLE ... RENAME TO SQL when table name changes."""
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())
    CreateModel(
        name="Widget",
        fields=[("id", fields.IntField(pk=True))],
    ).state_forward("models", state)

    op = RenameModel(old_name="Widget", new_name="Gadget")

    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" RENAME TO "gadget"'


@pytest.mark.asyncio
async def test_alter_field_forward_null_change() -> None:
    """AlterField null=False to null=True should DROP NOT NULL; reverse should SET NOT NULL."""
    # Forward: null=False -> null=True (DROP NOT NULL)
    OldModel = make_model(
        "Widget",
        id=fields.IntField(pk=True),
        name=fields.TextField(),
    )
    NewModel = make_model(
        "Widget",
        id=fields.IntField(pk=True),
        name=fields.TextField(null=True),
    )

    old_state = build_state("models", OldModel)
    new_state = build_state("models", NewModel)

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    op = AlterField(model_name="Widget", name="name", field=fields.TextField(null=True))

    await op.database_forward("models", old_state, new_state, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" ALTER COLUMN "name" DROP NOT NULL'

    # Reverse: null=True -> null=False (SET NOT NULL)
    reverse_client = FakeClient("sql")
    reverse_editor = TestSchemaEditor(reverse_client)
    reverse_op = AlterField(model_name="Widget", name="name", field=fields.TextField())

    await reverse_op.database_forward("models", new_state, old_state, state_editor=reverse_editor)

    assert len(reverse_client.executed) == 1
    assert reverse_client.executed[0] == 'ALTER TABLE "widget" ALTER COLUMN "name" SET NOT NULL'


@pytest.mark.asyncio
async def test_alter_field_forward_db_default_change() -> None:
    """AlterField should SET DEFAULT when adding db_default and DROP DEFAULT when removing it."""
    # Forward: no db_default -> db_default=42 (SET DEFAULT)
    OldModel = make_model(
        "Widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(),
    )
    NewModel = make_model(
        "Widget",
        id=fields.IntField(pk=True),
        score=fields.IntField(db_default=42),
    )

    old_state = build_state("models", OldModel)
    new_state = build_state("models", NewModel)

    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    op = AlterField(model_name="Widget", name="score", field=fields.IntField(db_default=42))

    await op.database_forward("models", old_state, new_state, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'ALTER TABLE "widget" ALTER COLUMN "score" SET DEFAULT 42'

    # Reverse: db_default=42 -> no db_default (DROP DEFAULT)
    drop_client = FakeClient("sql")
    drop_editor = TestSchemaEditor(drop_client)
    drop_op = AlterField(model_name="Widget", name="score", field=fields.IntField())

    await drop_op.database_forward("models", new_state, old_state, state_editor=drop_editor)

    assert len(drop_client.executed) == 1
    assert drop_client.executed[0] == 'ALTER TABLE "widget" ALTER COLUMN "score" DROP DEFAULT'


@pytest.mark.asyncio
async def test_run_sql_forward_and_backward() -> None:
    """RunSQL should execute forward SQL and reverse SQL."""
    client = FakeClient("sql")
    editor = TestSchemaEditor(client)
    state = State(models={}, apps=StateApps())

    op = RunSQL(
        'CREATE INDEX "idx_widget_name" ON "widget" ("name")',
        reverse_sql='DROP INDEX "idx_widget_name"',
    )

    # Forward
    await op.run("models", state, dry_run=False, state_editor=editor)

    assert len(client.executed) == 1
    assert client.executed[0] == 'CREATE INDEX "idx_widget_name" ON "widget" ("name")'

    # Backward
    backward_client = FakeClient("sql")
    backward_editor = TestSchemaEditor(backward_client)

    await op.database_backward("models", state, state, state_editor=backward_editor)

    assert len(backward_client.executed) == 1
    assert backward_client.executed[0] == 'DROP INDEX "idx_widget_name"'
