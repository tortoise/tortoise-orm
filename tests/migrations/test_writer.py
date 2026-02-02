from __future__ import annotations

import functools
import textwrap
from pathlib import Path

import pytest

from tortoise import fields
from tortoise.indexes import Index, PartialIndex
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.operations import (
    AddConstraint,
    AddIndex,
    AlterField,
    CreateModel,
    RenameField,
    RunPython,
)
from tortoise.migrations.writer import MigrationWriter


def _prepare_migration_package(tmp_path: Path, app_label: str) -> str:
    package_dir = tmp_path / app_label
    migrations_dir = package_dir / "migrations"
    migrations_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="ascii")
    (migrations_dir / "__init__.py").write_text("", encoding="ascii")
    return f"{app_label}.migrations"


def _write_migration(
    tmp_path: Path,
    monkeypatch,
    name: str,
    operations,
    expected: str,
) -> None:
    module_path = _prepare_migration_package(tmp_path, "app")
    monkeypatch.syspath_prepend(str(tmp_path))

    writer = MigrationWriter(
        name,
        "app",
        operations,
        migrations_module=module_path,
    )
    migration_path = writer.write()
    content = migration_path.read_text(encoding="ascii")
    assert content == expected


def test_writer_format_create_model_basic(tmp_path: Path, monkeypatch) -> None:
    operations = [
        CreateModel(
            name="Widget",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("name", fields.CharField(max_length=100)),
            ],
        )
    ]
    expected = textwrap.dedent(
        """\
        from tortoise import migrations
        from tortoise.migrations import operations as ops
        from tortoise import fields

        class Migration(migrations.Migration):
            operations = [
                ops.CreateModel(
                    name='Widget',
                    fields=[
                        ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                        ('name', fields.CharField(max_length=100)),
                    ],
                ),
            ]
        """
    )
    _write_migration(tmp_path, monkeypatch, "0001_initial", operations, expected)


def test_writer_format_rename_and_alter(tmp_path: Path, monkeypatch) -> None:
    operations = [
        RenameField(model_name="Widget", old_name="title", new_name="name"),
        AlterField(
            model_name="Widget",
            name="name",
            field=fields.CharField(max_length=120, null=True),
        ),
    ]
    expected = textwrap.dedent(
        """\
        from tortoise import migrations
        from tortoise.migrations import operations as ops
        from tortoise import fields

        class Migration(migrations.Migration):
            operations = [
                ops.RenameField(
                    model_name='Widget',
                    old_name='title',
                    new_name='name',
                ),
                ops.AlterField(
                    model_name='Widget',
                    name='name',
                    field=fields.CharField(null=True, max_length=120),
                ),
            ]
        """
    )
    _write_migration(tmp_path, monkeypatch, "0002_rename_alter", operations, expected)


def test_writer_format_options_indexes_constraints(tmp_path: Path, monkeypatch) -> None:
    operations = [
        CreateModel(
            name="Widget",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("name", fields.CharField(max_length=100)),
                ("status", fields.CharField(max_length=20)),
            ],
            options={
                "unique_together": (("name",),),
                "indexes": [
                    Index(fields=("name",), name="idx_widget_name"),
                    PartialIndex(
                        fields=("status",), name="idx_widget_status", condition={"active": True}
                    ),
                ],
                "constraints": [
                    UniqueConstraint(fields=("name", "status"), name="uniq_widget_name_status"),
                ],
            },
        ),
        AddIndex("Widget", Index(fields=("name",), name="idx_widget_name")),
        AddConstraint("Widget", UniqueConstraint(fields=("name",), name="uniq_widget_name")),
    ]
    expected = textwrap.dedent(
        """\
        from tortoise import migrations
        from tortoise.migrations import operations as ops
        from tortoise import fields
        from tortoise.indexes import Index, PartialIndex
        from tortoise.migrations.constraints import UniqueConstraint

        class Migration(migrations.Migration):
            operations = [
                ops.CreateModel(
                    name='Widget',
                    fields=[
                        ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                        ('name', fields.CharField(max_length=100)),
                        ('status', fields.CharField(max_length=20)),
                    ],
                    options={'unique_together': (('name',),), 'indexes': [Index(fields=['name'], name='idx_widget_name'), PartialIndex(fields=['status'], name='idx_widget_status', condition={'active': True})], 'constraints': [UniqueConstraint(fields=('name', 'status'), name='uniq_widget_name_status')]},
                ),
                ops.AddIndex(
                    model_name='Widget',
                    index=Index(fields=['name'], name='idx_widget_name'),
                ),
                ops.AddConstraint(
                    model_name='Widget',
                    constraint=UniqueConstraint(fields=('name',), name='uniq_widget_name'),
                ),
            ]
        """
    )
    _write_migration(tmp_path, monkeypatch, "0003_options", operations, expected)


def test_writer_renders_fk_field(tmp_path: Path, monkeypatch) -> None:
    operations = [
        CreateModel(
            name="Author",
            fields=[("id", fields.IntField(primary_key=True))],
        ),
        CreateModel(
            name="Post",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("author", fields.ForeignKeyField("app.Author", related_name="posts")),
            ],
        ),
    ]
    expected = textwrap.dedent(
        """\
        from tortoise import migrations
        from tortoise.migrations import operations as ops
        from tortoise.fields.base import OnDelete
        from tortoise import fields

        class Migration(migrations.Migration):
            operations = [
                ops.CreateModel(
                    name='Author',
                    fields=[
                        ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                    ],
                ),
                ops.CreateModel(
                    name='Post',
                    fields=[
                        ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                        ('author', fields.ForeignKeyField('app.Author', db_constraint=True, related_name='posts', on_delete=OnDelete.CASCADE)),
                    ],
                ),
            ]
        """
    )
    _write_migration(tmp_path, monkeypatch, "0004_fk", operations, expected)


def test_writer_excludes_fk_source_field(tmp_path: Path, monkeypatch) -> None:
    operations = [
        CreateModel(
            name="Post",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                ("author", fields.ForeignKeyField("app.Author", related_name="posts")),
                ("author_id", fields.IntField(source_field="author_id")),
            ],
        )
    ]
    expected = textwrap.dedent(
        """\
        from tortoise import migrations
        from tortoise.migrations import operations as ops
        from tortoise.fields.base import OnDelete
        from tortoise import fields

        class Migration(migrations.Migration):
            operations = [
                ops.CreateModel(
                    name='Post',
                    fields=[
                        ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                        ('author', fields.ForeignKeyField('app.Author', db_constraint=True, related_name='posts', on_delete=OnDelete.CASCADE)),
                    ],
                ),
            ]
        """
    )
    _write_migration(tmp_path, monkeypatch, "0005_fk_source", operations, expected)


def test_writer_serializes_on_delete_enum(tmp_path: Path, monkeypatch) -> None:
    operations = [
        CreateModel(
            name="Post",
            fields=[
                ("id", fields.IntField(primary_key=True)),
                (
                    "author",
                    fields.ForeignKeyField(
                        "app.Author",
                        related_name="posts",
                        on_delete=fields.OnDelete.SET_NULL,
                        null=True,
                    ),
                ),
            ],
        )
    ]
    expected = textwrap.dedent(
        """\
        from tortoise import migrations
        from tortoise.migrations import operations as ops
        from tortoise.fields.base import OnDelete
        from tortoise import fields

        class Migration(migrations.Migration):
            operations = [
                ops.CreateModel(
                    name='Post',
                    fields=[
                        ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                        ('author', fields.ForeignKeyField('app.Author', null=True, db_constraint=True, related_name='posts', on_delete=OnDelete.SET_NULL)),
                    ],
                ),
            ]
        """
    )
    _write_migration(tmp_path, monkeypatch, "0006_enum", operations, expected)


def test_writer_skips_missing_db_index(tmp_path: Path, monkeypatch) -> None:
    operations = [
        CreateModel(
            name="Message",
            fields=[("body", fields.TextField())],
        )
    ]
    expected = textwrap.dedent(
        """\
        from tortoise import migrations
        from tortoise.migrations import operations as ops
        from tortoise import fields

        class Migration(migrations.Migration):
            operations = [
                ops.CreateModel(
                    name='Message',
                    fields=[
                        ('body', fields.TextField(unique=False)),
                    ],
                ),
            ]
        """
    )
    _write_migration(tmp_path, monkeypatch, "0007_textfield", operations, expected)


def test_writer_rejects_lambda_default(tmp_path: Path, monkeypatch) -> None:
    operations = [
        AlterField(
            model_name="Widget",
            name="name",
            field=fields.CharField(max_length=120, default=lambda: "x"),
        )
    ]
    module_path = _prepare_migration_package(tmp_path, "app")
    monkeypatch.syspath_prepend(str(tmp_path))
    writer = MigrationWriter(
        "0004_lambda",
        "app",
        operations,
        migrations_module=module_path,
    )
    with pytest.raises(ValueError, match="Cannot serialize lambda"):
        writer.as_string()


def _default_value() -> str:
    return "ok"


def test_writer_allows_partial_default(tmp_path: Path, monkeypatch) -> None:
    operations = [
        AlterField(
            model_name="Widget",
            name="name",
            field=fields.CharField(max_length=120, default=functools.partial(_default_value)),
        )
    ]
    module_path = _prepare_migration_package(tmp_path, "app")
    monkeypatch.syspath_prepend(str(tmp_path))
    writer = MigrationWriter(
        "0005_partial",
        "app",
        operations,
        migrations_module=module_path,
    )
    content = writer.as_string()
    assert "functools.partial" in content


def test_writer_rejects_partial_lambda(tmp_path: Path, monkeypatch) -> None:
    operations = [
        AlterField(
            model_name="Widget",
            name="name",
            field=fields.CharField(max_length=120, default=functools.partial(lambda: "x")),
        )
    ]
    module_path = _prepare_migration_package(tmp_path, "app")
    monkeypatch.syspath_prepend(str(tmp_path))
    writer = MigrationWriter(
        "0006_partial_lambda",
        "app",
        operations,
        migrations_module=module_path,
    )
    with pytest.raises(ValueError, match="lambda"):
        writer.as_string()


def test_writer_rejects_local_function_default(tmp_path: Path, monkeypatch) -> None:
    def _local_default() -> str:
        return "local"

    operations = [
        AlterField(
            model_name="Widget",
            name="name",
            field=fields.CharField(max_length=120, default=_local_default),
        )
    ]
    module_path = _prepare_migration_package(tmp_path, "app")
    monkeypatch.syspath_prepend(str(tmp_path))
    writer = MigrationWriter(
        "0007_local_default",
        "app",
        operations,
        migrations_module=module_path,
    )
    with pytest.raises(ValueError, match="local function"):
        writer.as_string()


def _runpython_forward(apps, schema_editor) -> None:
    _ = (apps, schema_editor)


def _runpython_reverse(apps, schema_editor) -> None:
    _ = (apps, schema_editor)


def test_writer_format_runpython(tmp_path: Path, monkeypatch) -> None:
    operations = [RunPython(_runpython_forward, reverse_code=_runpython_reverse, atomic=False)]
    expected = textwrap.dedent(
        """\
        from tortoise import migrations
        from tortoise.migrations import operations as ops
        from tests.migrations.test_writer import _runpython_forward, _runpython_reverse

        class Migration(migrations.Migration):
            operations = [
                ops.RunPython(
                    code=_runpython_forward,
                    reverse_code=_runpython_reverse,
                    atomic=False,
                ),
            ]
        """
    )
    _write_migration(tmp_path, monkeypatch, "0008_runpython", operations, expected)
