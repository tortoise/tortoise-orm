from __future__ import annotations

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.migrations.migration import Migration
from tortoise.migrations.operations import CreateModel, DeleteModel, RemoveField
from tortoise.migrations.schema_editor.sqlite import SqliteSchemaEditor
from tortoise.migrations.schema_generator.state import State
from tortoise.migrations.schema_generator.state_apps import StateApps


def _create_ops() -> list[CreateModel]:
    return [
        CreateModel(
            name="Permission",
            fields=[("id", fields.IntField(primary_key=True))],
            options={"table": "perm", "app": "models"},
        ),
        CreateModel(
            name="Role",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                (
                    "permissions",
                    fields.ManyToManyField(
                        "models.Permission", related_name="roles", through="role_perms"
                    ),
                ),
            ],
            options={"table": "role", "app": "models"},
        ),
        CreateModel(
            name="RolePermission",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("mask", fields.IntField(default=0)),
                ("role", fields.ForeignKeyField("models.Role", related_name="ref_perm")),
            ],
            options={"table": "role_perms", "app": "models"},
        ),
    ]


def _editor() -> SqliteSchemaEditor:
    return SqliteSchemaEditor(FakeClient("sqlite"), collect_sql=True)


@pytest.mark.asyncio
async def test_m2m_through_table_owned_by_explicit_model_created_once() -> None:
    migration = Migration("0001_initial", "models")
    migration.operations = _create_ops()
    editor = _editor()
    await migration.apply(
        State(models={}, apps=StateApps()), schema_editor=editor, collect_sql=True
    )

    sql = "\n".join(editor.collected_sql)
    assert sql.count('CREATE TABLE "role_perms"') == 1
    assert '"mask"' in sql


@pytest.mark.asyncio
async def test_m2m_through_table_dropped_once_on_rollback() -> None:
    migration = Migration("0001_initial", "models")
    migration.operations = _create_ops()
    state = await migration.apply(State(models={}, apps=StateApps()))

    editor = _editor()
    await migration.unapply(state, schema_editor=editor, collect_sql=True)
    assert "\n".join(editor.collected_sql).count('DROP TABLE "role_perms"') == 1


@pytest.mark.asyncio
async def test_m2m_through_table_dropped_once_when_field_and_model_removed() -> None:
    initial = Migration("0001_initial", "models")
    initial.operations = _create_ops()
    removal = Migration("0002_remove", "models")
    removal.operations = [RemoveField("Role", "permissions"), DeleteModel("RolePermission")]
    state = await initial.apply(State(models={}, apps=StateApps()))

    editor = _editor()
    await removal.apply(state, schema_editor=editor, collect_sql=True)
    assert "\n".join(editor.collected_sql).count('DROP TABLE "role_perms"') == 1


@pytest.mark.asyncio
async def test_converting_implicit_through_to_explicit_model_drops_then_creates() -> None:
    ops = _create_ops()
    initial = Migration("0001_initial", "models")
    initial.operations = ops[:2]
    convert = Migration("0002_convert", "models")
    convert.operations = [RemoveField("Role", "permissions"), ops[2]]
    state = await initial.apply(State(models={}, apps=StateApps()))

    editor = _editor()
    await convert.apply(state, schema_editor=editor, collect_sql=True)
    sql = "\n".join(editor.collected_sql)
    assert sql.count('DROP TABLE "role_perms"') == 1
    assert sql.count('CREATE TABLE "role_perms"') == 1


@pytest.mark.asyncio
async def test_generated_explicit_to_implicit_through_conversion() -> None:
    from tortoise.migrations.schema_generator.operation_generator import OperationGenerator

    ops = _create_ops()
    old_migration = Migration("0001_initial", "models")
    old_migration.operations = [
        ops[0],
        CreateModel(
            name="Owner",
            fields=[("id", fields.IntField(primary_key=True))],
            options={"table": "owner", "app": "models"},
        ),
        CreateModel(
            name="RolePermission",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("mask", fields.IntField(default=0)),
                ("owner", fields.ForeignKeyField("models.Owner", related_name="ref_perm")),
            ],
            options={"table": "role_perms", "app": "models"},
        ),
    ]
    old_state = await old_migration.apply(State(models={}, apps=StateApps()))

    new_migration = Migration("0001_new", "models")
    new_migration.operations = [
        ops[0],
        CreateModel(
            name="Owner",
            fields=[("id", fields.IntField(primary_key=True))],
            options={"table": "owner", "app": "models"},
        ),
        CreateModel(
            name="Role",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("title", fields.CharField(max_length=20)),
                (
                    "permissions",
                    fields.ManyToManyField(
                        "models.Permission", related_name="roles", through="role_perms"
                    ),
                ),
            ],
            options={"table": "role", "app": "models"},
        ),
    ]
    new_state = await new_migration.apply(State(models={}, apps=StateApps()))

    migration = Migration("0002_convert", "models")
    migration.operations = OperationGenerator(old_state, new_state).generate()
    editor = _editor()
    await migration.apply(old_state, schema_editor=editor, collect_sql=True)
    sql = "\n".join(editor.collected_sql)
    assert sql.count('DROP TABLE "role_perms"') == 1
    assert sql.count('CREATE TABLE "role_perms"') == 1
    assert sql.index('DROP TABLE "role_perms"') < sql.index('CREATE TABLE "role_perms"')


def _role_ops(with_explicit: bool) -> list[CreateModel]:
    ops = [
        CreateModel(
            name="Permission",
            fields=[("id", fields.IntField(primary_key=True))],
            options={"table": "perm", "app": "models"},
        ),
        CreateModel(
            name="Role",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("title", fields.CharField(max_length=20)),
                (
                    "permissions",
                    fields.ManyToManyField(
                        "models.Permission", related_name="roles", through="role_perms"
                    ),
                ),
            ],
            options={"table": "role", "app": "models"},
        ),
    ]
    if with_explicit:
        ops.append(
            CreateModel(
                name="RolePermission",
                fields=[
                    ("id", fields.IntField(primary_key=True)),
                    ("mask", fields.IntField(default=0)),
                    ("role", fields.ForeignKeyField("models.Role", related_name="ref_perm")),
                ],
                options={"table": "role_perms", "app": "models"},
            )
        )
    return ops


async def _convert_sql(from_explicit: bool) -> str:
    from tortoise.migrations.schema_generator.operation_generator import OperationGenerator

    old_m = Migration("0001_old", "models")
    old_m.operations = _role_ops(from_explicit)
    old_state = await old_m.apply(State(models={}, apps=StateApps()))
    new_m = Migration("0001_new", "models")
    new_m.operations = _role_ops(not from_explicit)
    new_state = await new_m.apply(State(models={}, apps=StateApps()))

    migration = Migration("0002_convert", "models")
    migration.operations = OperationGenerator(old_state, new_state).generate()
    editor = _editor()
    await migration.apply(old_state, schema_editor=editor, collect_sql=True)
    return "\n".join(editor.collected_sql)


@pytest.mark.asyncio
async def test_generated_implicit_to_explicit_with_unchanged_m2m_field() -> None:
    sql = await _convert_sql(from_explicit=False)
    assert sql.count('DROP TABLE "role_perms"') == 1
    assert sql.count('CREATE TABLE "role_perms"') == 1
    assert sql.index('DROP TABLE "role_perms"') < sql.index('CREATE TABLE "role_perms"')
    assert '"mask"' in sql


@pytest.mark.asyncio
async def test_generated_explicit_to_implicit_with_unchanged_m2m_field() -> None:
    sql = await _convert_sql(from_explicit=True)
    assert sql.count('DROP TABLE "role_perms"') == 1
    assert sql.count('CREATE TABLE "role_perms"') == 1
    assert sql.index('DROP TABLE "role_perms"') < sql.index('CREATE TABLE "role_perms"')
    assert '"mask"' not in sql


@pytest.mark.asyncio
async def test_add_m2m_field_before_creating_explicit_through_model() -> None:
    ops = _role_ops(True)
    role = ops[1]
    m2m = dict(role.fields)["permissions"]
    base = Migration("0001_initial", "models")
    base.operations = [
        ops[0],
        CreateModel(
            name="Role",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("title", fields.CharField(max_length=20)),
            ],
            options={"table": "role", "app": "models"},
        ),
    ]
    state = await base.apply(State(models={}, apps=StateApps()))
    from tortoise.migrations.operations import AddField

    migration = Migration("0002_m2m", "models")
    migration.operations = [AddField("Role", "permissions", m2m), ops[2]]
    editor = _editor()
    await migration.apply(state, schema_editor=editor, collect_sql=True)
    sql = "\n".join(editor.collected_sql)
    assert sql.count('CREATE TABLE "role_perms"') == 1
    assert '"mask"' in sql
