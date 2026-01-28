from __future__ import annotations

import importlib.util
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import pytest

from tests.utils.fake_client import FakeClient
from tortoise import fields
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.contrib.postgres.fields import TSVectorField
from tortoise.fields.relational import ForeignKeyFieldInstance, ManyToManyRelation
from tortoise.indexes import Index, PartialIndex
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_editor.base_postgres import BasePostgresSchemaEditor
from tortoise.migrations.schema_editor.mssql import MSSQLSchemaEditor
from tortoise.migrations.schema_editor.mysql import MySQLSchemaEditor
from tortoise.migrations.schema_editor.oracle import OracleSchemaEditor
from tortoise.migrations.schema_editor.sqlite import SqliteSchemaEditor
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


def load_schema_generator(module_path: Path, class_name: str) -> type[BaseSchemaGenerator]:
    module_name = f"_schema_gen_{class_name}_{module_path.stat().st_mtime_ns}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load schema generator from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


def init_apps(*models: type[Model]) -> None:
    apps = StateApps()
    for model in models:
        apps.register_model("models", model)
    apps._init_relations()


def build_models(
    *,
    with_fk: bool,
    with_m2m: bool,
    with_indexes: bool,
    with_index_objects: bool,
) -> tuple[type[Model], Iterable[type[Model]]]:
    class Category(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()

        class Meta:
            app = "models"
            table = "category"

    class Tag(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()

        class Meta:
            app = "models"
            table = "tag"

    class Widget(Model):
        id = fields.IntField(pk=True)
        name = fields.TextField()
        if with_fk:
            category: ForeignKeyFieldInstance[Any] = fields.ForeignKeyField(
                "models.Category", related_name="widgets"
            )
        if with_m2m:
            tags: ManyToManyRelation[Any] = fields.ManyToManyField(
                "models.Tag", related_name="widgets"
            )
        if with_indexes:
            age: fields.IntField = fields.IntField(index=True)

        class Meta:
            app = "models"
            table = "widget"
            if with_indexes:
                unique_together = (("name", "age"),)
                indexes = cast(tuple[object, ...], (("name",),))
            if with_index_objects:
                indexes = cast(
                    tuple[object, ...],
                    (
                        Index(fields=("name",), name="idx_widget_name_custom"),
                        PartialIndex(fields=("name",), condition={"name": "alpha"}),
                    ),
                )

    models: list[type[Model]] = [Widget]
    if with_fk:
        models.append(Category)
    if with_m2m:
        models.append(Tag)
    init_apps(*models)
    return Widget, tuple(models)


def normalize_statements(sql: str) -> list[str]:
    parts = [part.strip() for part in re.split(r";\s*", sql) if part.strip()]
    normalized = []
    for part in parts:
        part = part.replace("IF NOT EXISTS ", "")
        part = re.sub(r"\s+", " ", part)
        normalized.append(part.strip())
    return normalized


def schema_editor_sql(editor: BaseSchemaEditor, model: type[Model]) -> list[str]:
    sql_data = editor._get_model_sql_data(model)
    combined = "\n".join([sql_data.table_sql, *sql_data.m2m_tables_sql])
    return normalize_statements(combined)


def schema_generator_sql(
    generator_cls: type[BaseSchemaGenerator],
    client: BaseDBAsyncClient,
    model: type[Model],
    models: Iterable[type[Model]],
) -> list[str]:
    class TestGenerator(generator_cls):  # type: ignore[misc, valid-type]
        def __init__(
            self, client: BaseDBAsyncClient, models_to_create: Iterable[type[Model]]
        ) -> None:
            super().__init__(client)
            self._models_to_create = list(models_to_create)

        def _get_models_to_create(self) -> list[type[Model]]:
            return list(self._models_to_create)

    generator = TestGenerator(client, models)
    data = generator._get_table_sql(model, safe=False)
    combined = "\n".join([data["table_creation_string"], *data["m2m_tables"]])
    return normalize_statements(combined)


BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_GENERATORS = [
    (
        SqliteSchemaEditor,
        BASE_DIR / "tortoise" / "backends" / "sqlite" / "schema_generator.py",
        "SqliteSchemaGenerator",
        {"dialect": "sqlite", "inline_comment": True},
    ),
    (
        BasePostgresSchemaEditor,
        BASE_DIR / "tortoise" / "backends" / "base_postgres" / "schema_generator.py",
        "BasePostgresSchemaGenerator",
        {"dialect": "postgres", "inline_comment": False},
    ),
    (
        MySQLSchemaEditor,
        BASE_DIR / "tortoise" / "backends" / "mysql" / "schema_generator.py",
        "MySQLSchemaGenerator",
        {"dialect": "mysql", "inline_comment": True, "charset": "utf8mb4"},
    ),
    (
        MSSQLSchemaEditor,
        BASE_DIR / "tortoise" / "backends" / "mssql" / "schema_generator.py",
        "MSSQLSchemaGenerator",
        {"dialect": "mssql", "inline_comment": False},
    ),
    (
        OracleSchemaEditor,
        BASE_DIR / "tortoise" / "backends" / "oracle" / "schema_generator.py",
        "OracleSchemaGenerator",
        {"dialect": "oracle", "inline_comment": False},
    ),
]


@pytest.mark.parametrize(
    ("editor_cls", "generator_path", "generator_name", "client_kwargs"),
    BACKEND_GENERATORS,
)
@pytest.mark.parametrize(
    "scenario",
    [
        {"with_fk": False, "with_m2m": False, "with_indexes": False, "with_index_objects": False},
        {"with_fk": True, "with_m2m": False, "with_indexes": False, "with_index_objects": False},
        {"with_fk": False, "with_m2m": True, "with_indexes": False, "with_index_objects": False},
        {"with_fk": False, "with_m2m": False, "with_indexes": True, "with_index_objects": False},
        {"with_fk": True, "with_m2m": True, "with_indexes": True, "with_index_objects": False},
        {"with_fk": False, "with_m2m": False, "with_indexes": False, "with_index_objects": True},
        {"with_fk": True, "with_m2m": True, "with_indexes": False, "with_index_objects": True},
    ],
)
def test_schema_editor_matches_schema_generator(
    editor_cls: type[BaseSchemaEditor],
    generator_path: Path,
    generator_name: str,
    client_kwargs: dict,
    scenario: dict,
) -> None:
    model, models = build_models(**scenario)
    client = FakeClient(**client_kwargs)
    editor = editor_cls(client)
    generator_cls = load_schema_generator(generator_path, generator_name)

    editor_statements = schema_editor_sql(editor, model)
    generator_statements = schema_generator_sql(generator_cls, client, model, models)

    assert editor_statements == generator_statements


def test_schema_editor_matches_schema_generator_for_generated_column() -> None:
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
            app = "models"
            table = "search_document"

    init_apps(SearchDocument)
    client = FakeClient(dialect="postgres", inline_comment=False)
    editor = BasePostgresSchemaEditor(client)
    generator_cls = load_schema_generator(
        BASE_DIR / "tortoise" / "backends" / "base_postgres" / "schema_generator.py",
        "BasePostgresSchemaGenerator",
    )

    editor_statements = schema_editor_sql(editor, SearchDocument)
    generator_statements = schema_generator_sql(
        generator_cls, client, SearchDocument, (SearchDocument,)
    )

    assert editor_statements == generator_statements
    assert any("GENERATED ALWAYS AS" in stmt for stmt in editor_statements)
