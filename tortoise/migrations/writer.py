from __future__ import annotations

import datetime as dt
import functools
import importlib
import inspect
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from pypika_tortoise.context import DEFAULT_SQL_CONTEXT

from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.operations import (
    AddConstraint,
    AddField,
    AddIndex,
    AlterField,
    AlterModelOptions,
    CreateModel,
    CreateSchema,
    DeleteModel,
    DropSchema,
    Operation,
    RemoveConstraint,
    RemoveField,
    RemoveIndex,
    RenameConstraint,
    RenameField,
    RenameIndex,
    RenameModel,
    RunPython,
    SQLOperation,
)

_MIGRATION_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def slugify_migration_name(value: str) -> str:
    slug = value.strip().lower().replace(" ", "_")
    slug = _MIGRATION_SLUG_RE.sub("_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "auto"


def format_migration_name(number: int, name: str) -> str:
    return f"{number:04d}_{slugify_migration_name(name)}"


def migrations_module_path(module_name: str) -> Path:
    module = importlib.import_module(module_name)
    if not hasattr(module, "__path__"):
        raise ValueError(f"Migration module {module_name} is not a package")
    return Path(next(iter(module.__path__)))


@dataclass
class ImportManager:
    imports: dict[str, set[str]] = dataclass_field(default_factory=dict)
    modules: set[str] = dataclass_field(default_factory=set)
    uses_fields_module: bool = False
    uses_indexes: set[str] = dataclass_field(default_factory=set)
    uses_constraints: bool = False

    def add_from(self, module: str, name: str) -> None:
        self.imports.setdefault(module, set()).add(name)

    def add_module(self, module: str) -> None:
        self.modules.add(module)

    def add_fields_alias(self) -> None:
        self.uses_fields_module = True

    def add_index_class(self, name: str) -> None:
        self.uses_indexes.add(name)

    def add_constraints(self) -> None:
        self.uses_constraints = True

    def render(self) -> list[str]:
        lines: list[str] = []
        for module in sorted(self.modules):
            lines.append(f"import {module}")
        for module, names in sorted(self.imports.items()):
            lines.append(f"from {module} import {', '.join(sorted(names))}")
        if self.uses_fields_module:
            lines.append("from tortoise import fields")
        if self.uses_indexes:
            index_names = ", ".join(sorted(self.uses_indexes))
            lines.append(f"from tortoise.indexes import {index_names}")
        if self.uses_constraints:
            lines.append("from tortoise.migrations.constraints import UniqueConstraint")
        return lines


def _resolve_import(value: Any) -> tuple[str, str, bool]:
    module_name = value.__module__
    module = importlib.import_module(module_name)
    for name, obj in module.__dict__.items():
        if obj is value:
            return module_name, name, False
    qualname = getattr(value, "__qualname__", None)
    if qualname and "." in qualname:
        if "<locals>" in qualname:
            raise ValueError(f"Cannot resolve import for {value!r}")
        return module_name, f"{module_name}.{qualname}", True
    name = getattr(value, "__name__", None)
    if name:
        return module_name, name, False
    raise ValueError(f"Cannot resolve import for {value!r}")


def render_value(value: Any, imports: ImportManager) -> str:
    # StrEnum instances are both str and Enum, so check Enum first
    if isinstance(value, Enum):
        enum_cls = value.__class__
        module_name, name, use_module = _resolve_import(enum_cls)
        if use_module:
            imports.add_module(module_name)
            return f"{name}.{value.name}"
        imports.add_from(module_name, name)
        return f"{name}.{value.name}"
    if value is None or isinstance(value, (bool, int, float, str)):
        return repr(value)
    if isinstance(value, bytes):
        return repr(value)
    if hasattr(value, "get_sql") and callable(value.get_sql):
        sql = value.get_sql(DEFAULT_SQL_CONTEXT)
        imports.add_from("tortoise.migrations.expressions", "RawSQLTerm")
        return f"RawSQLTerm({sql!r})"
    if isinstance(value, list):
        return "[" + ", ".join(render_value(item, imports) for item in value) + "]"
    if isinstance(value, tuple):
        if len(value) == 1:
            return f"({render_value(value[0], imports)},)"
        return "(" + ", ".join(render_value(item, imports) for item in value) + ")"
    if isinstance(value, dict):
        items = [
            f"{render_value(key, imports)}: {render_value(val, imports)}"
            for key, val in value.items()
        ]
        return "{" + ", ".join(items) + "}"
    if isinstance(value, Decimal):
        imports.add_from("decimal", "Decimal")
        return f"Decimal({str(value)!r})"
    if isinstance(value, uuid.UUID):
        imports.add_module("uuid")
        return f"uuid.UUID({str(value)!r})"
    if isinstance(value, (dt.datetime, dt.date, dt.time, dt.timedelta)):
        imports.add_module("datetime")
        if isinstance(value, dt.timedelta):
            return f"datetime.timedelta(seconds={value.total_seconds()!r})"
        cls_name = value.__class__.__name__
        return f"datetime.{cls_name}.fromisoformat({value.isoformat()!r})"
    if isinstance(value, functools.partial):
        func = value.func
        if getattr(func, "__name__", "") == "<lambda>":
            raise ValueError(
                "Cannot serialize lambda inside functools.partial; use a module-level function."
            )
        if hasattr(func, "__qualname__") and "<locals>" in func.__qualname__:
            raise ValueError(f"Cannot serialize partial with local function: {func!r}")
        args = ", ".join(render_value(arg, imports) for arg in value.args)
        kwargs = (
            ", ".join(f"{key}={render_value(val, imports)}" for key, val in value.keywords.items())
            if value.keywords
            else ""
        )
        parts = ", ".join(part for part in (args, kwargs) if part)
        module_name, name, use_module = _resolve_import(func)
        if use_module:
            imports.add_module(module_name)
            func_ref = name
        else:
            imports.add_from(module_name, name)
            func_ref = name
        imports.add_module("functools")
        return f"functools.partial({', '.join([func_ref, parts]) if parts else func_ref})"
    # Check type before inspect.isfunction (classes are callable too)
    if isinstance(value, type):
        if value.__module__ == "builtins":
            return value.__name__
        module_name, name, use_module = _resolve_import(value)
        if use_module:
            imports.add_module(module_name)
            return name
        imports.add_from(module_name, name)
        return name
    if inspect.isfunction(value) or callable(value):
        if getattr(value, "__name__", "") == "<lambda>":
            raise ValueError("Cannot serialize lambda; use a module-level function instead.")
        if hasattr(value, "__qualname__") and "<locals>" in value.__qualname__:
            raise ValueError(f"Cannot serialize local function: {value!r}")
        module_name, name, use_module = _resolve_import(value)
        if use_module:
            imports.add_module(module_name)
            return name
        imports.add_from(module_name, name)
        return name
    return repr(value)


def _render_call(path: str, args: list[Any], kwargs: dict[str, Any], imports: ImportManager) -> str:
    if path.startswith("tortoise.fields."):
        class_name = path.rsplit(".", 1)[1]
        # Render FieldInstance classes as their public Field name
        if class_name.endswith("FieldInstance"):
            class_name = class_name.replace("FieldInstance", "Field")
            # For relational fields, move model_name to first positional arg
            if path.startswith("tortoise.fields.relational.") and "model_name" in kwargs:
                args = [kwargs.pop("model_name")] + list(args)
        imports.add_fields_alias()
        callee = f"fields.{class_name}"
    elif path.startswith("tortoise.indexes."):
        class_name = path.rsplit(".", 1)[1]
        imports.add_index_class(class_name)
        callee = class_name
    elif path == "tortoise.migrations.constraints.UniqueConstraint":
        imports.add_constraints()
        callee = "UniqueConstraint"
    else:
        module, name = path.rsplit(".", 1)
        imports.add_from(module, name)
        callee = name

    rendered_args = [render_value(arg, imports) for arg in args]
    rendered_kwargs = [f"{key}={render_value(val, imports)}" for key, val in kwargs.items()]
    return f"{callee}({', '.join(rendered_args + rendered_kwargs)})"


class MigrationWriter:
    def __init__(
        self,
        name: str,
        app_label: str,
        operations: Iterable[Operation],
        *,
        dependencies: list[tuple[str, str]] | None = None,
        run_before: list[tuple[str, str]] | None = None,
        replaces: list[tuple[str, str]] | None = None,
        initial: bool | None = None,
        migrations_module: str | None = None,
    ) -> None:
        self.name = name
        self.app_label = app_label
        self.operations = list(operations)
        self.dependencies = dependencies or []
        self.run_before = run_before or []
        self.replaces = replaces or []
        self.initial = initial
        self.migrations_module = migrations_module

    def path(self) -> Path:
        if not self.migrations_module:
            raise ValueError("migrations_module is required to resolve the output path")
        return migrations_module_path(self.migrations_module) / f"{self.name}.py"

    def write(self) -> Path:
        path = self.path()
        path.write_text(self.as_string(), encoding="ascii")
        return path

    def as_string(self) -> str:
        imports = ImportManager()
        operations = []
        for operation in self.operations:
            operations.extend(self._format_operation(operation, imports, indent=" " * 8))

        lines: list[str] = [
            "from tortoise import migrations",
            "from tortoise.migrations import operations as ops",
        ]
        extra_imports = imports.render()
        if extra_imports:
            lines.extend(extra_imports)
        lines.extend(["", "class Migration(migrations.Migration):"])
        blocks: list[list[str]] = []
        if self.dependencies:
            blocks.append([f"    dependencies = {self.dependencies!r}"])
        if self.run_before:
            blocks.append([f"    run_before = {self.run_before!r}"])
        if self.replaces:
            blocks.append([f"    replaces = {self.replaces!r}"])
        if self.initial is not None:
            blocks.append([f"    initial = {self.initial!r}"])
        blocks.append(["    operations = [", *operations, "    ]"])
        for idx, block in enumerate(blocks):
            lines.extend(block)
            if idx < len(blocks) - 1:
                lines.append("")
        lines.append("")
        return "\n".join(lines)

    def _format_operation(
        self, operation: Operation, imports: ImportManager, *, indent: str
    ) -> list[str]:
        if isinstance(operation, CreateSchema):
            return [f"{indent}ops.CreateSchema(schema_name={operation.schema_name!r}),"]
        if isinstance(operation, DropSchema):
            return [f"{indent}ops.DropSchema(schema_name={operation.schema_name!r}),"]
        if isinstance(operation, CreateModel):
            return self._format_create_model(operation, imports, indent=indent)
        if isinstance(operation, DeleteModel):
            return [f"{indent}ops.DeleteModel(name={operation.name!r}),"]
        if isinstance(operation, RenameModel):
            return [
                f"{indent}ops.RenameModel(old_name={operation.old_name!r}, new_name={operation.new_name!r}),"
            ]
        if isinstance(operation, AddField):
            field_expr = self._render_field(operation.field, imports)
            return [
                f"{indent}ops.AddField(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    name={operation.name!r},",
                f"{indent}    field={field_expr},",
                f"{indent}),",
            ]
        if isinstance(operation, RemoveField):
            return [
                f"{indent}ops.RemoveField(model_name={operation.model_name!r}, name={operation.name!r}),"
            ]
        if isinstance(operation, AlterField):
            field_expr = self._render_field(operation.field, imports)
            return [
                f"{indent}ops.AlterField(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    name={operation.name!r},",
                f"{indent}    field={field_expr},",
                f"{indent}),",
            ]
        if isinstance(operation, RenameField):
            return [
                f"{indent}ops.RenameField(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    old_name={operation.old_name!r},",
                f"{indent}    new_name={operation.new_name!r},",
                f"{indent}),",
            ]
        if isinstance(operation, AlterModelOptions):
            options_expr = self._render_model_options(operation.options, imports)
            return [
                f"{indent}ops.AlterModelOptions(",
                f"{indent}    name={operation.name!r},",
                f"{indent}    options={options_expr},",
                f"{indent}),",
            ]
        if isinstance(operation, AddIndex):
            index_expr = self._render_index(operation.index, imports)
            return [
                f"{indent}ops.AddIndex(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    index={index_expr},",
                f"{indent}),",
            ]
        if isinstance(operation, RemoveIndex):
            return [
                f"{indent}ops.RemoveIndex(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    name={operation.name!r},",
                f"{indent}    fields={operation.fields!r},",
                f"{indent}),",
            ]
        if isinstance(operation, RenameIndex):
            return [
                f"{indent}ops.RenameIndex(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    new_name={operation.new_name!r},",
                f"{indent}    old_name={operation.old_name!r},",
                f"{indent}    old_fields={operation.old_fields!r},",
                f"{indent}),",
            ]
        if isinstance(operation, AddConstraint):
            constraint_expr = self._render_constraint(operation.constraint, imports)
            return [
                f"{indent}ops.AddConstraint(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    constraint={constraint_expr},",
                f"{indent}),",
            ]
        if isinstance(operation, RemoveConstraint):
            return [
                f"{indent}ops.RemoveConstraint(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    name={operation.name!r},",
                f"{indent}    fields={operation.fields!r},",
                f"{indent}),",
            ]
        if isinstance(operation, RenameConstraint):
            return [
                f"{indent}ops.RenameConstraint(",
                f"{indent}    model_name={operation.model_name!r},",
                f"{indent}    old_name={operation.old_name!r},",
                f"{indent}    new_name={operation.new_name!r},",
                f"{indent}),",
            ]
        if isinstance(operation, SQLOperation):
            values_expr = render_value(operation.values, imports)
            return [
                f"{indent}ops.SQLOperation(",
                f"{indent}    query={operation.query!r},",
                f"{indent}    values={values_expr},",
                f"{indent}),",
            ]
        if isinstance(operation, RunPython):
            code_expr = render_value(operation.code, imports)
            lines = [
                f"{indent}ops.RunPython(",
                f"{indent}    code={code_expr},",
            ]
            if operation.reverse_code is not None:
                reverse_expr = render_value(operation.reverse_code, imports)
                lines.append(f"{indent}    reverse_code={reverse_expr},")
            if operation.atomic is not None:
                lines.append(f"{indent}    atomic={operation.atomic!r},")
            lines.append(f"{indent}),")
            return lines
        raise ValueError(f"Unsupported operation type: {type(operation)!r}")

    def _render_field(self, field: Any, imports: ImportManager) -> str:
        path, args, kwargs = field.deconstruct()
        return _render_call(path, args, kwargs, imports)

    def _render_index(self, index: Any, imports: ImportManager) -> str:
        path, args, kwargs = index.deconstruct()
        return _render_call(path, args, kwargs, imports)

    def _render_constraint(self, constraint: UniqueConstraint, imports: ImportManager) -> str:
        path, args, kwargs = constraint.deconstruct()
        return _render_call(path, args, kwargs, imports)

    def _render_model_options(self, options: dict[str, Any], imports: ImportManager) -> str:
        rendered: dict[str, str] = {}
        for key, value in options.items():
            if key == "indexes":
                rendered[key] = (
                    "[" + ", ".join(self._render_index(item, imports) for item in value) + "]"
                )
                continue
            if key == "constraints":
                rendered[key] = (
                    "[" + ", ".join(self._render_constraint(item, imports) for item in value) + "]"
                )
                continue
            rendered[key] = render_value(value, imports)
        inner = ", ".join(f"{key!r}: {val}" for key, val in rendered.items())
        return "{" + inner + "}"

    def _format_create_model(
        self, operation: CreateModel, imports: ImportManager, *, indent: str
    ) -> list[str]:
        source_fields = {
            field.source_field
            for _, field in operation.fields
            if field is not None and hasattr(field, "source_field") and field.source_field
        }
        field_lines = []
        for name, field in operation.fields:
            if field is None:
                continue
            if name in source_fields:
                continue
            field_expr = self._render_field(field, imports)
            field_lines.append(f"{indent}        ({name!r}, {field_expr}),")
        fields_block = [f"{indent}    fields=["] + field_lines + [f"{indent}    ],"]

        options_block: list[str] = []
        if operation.options:
            options_expr = self._render_model_options(operation.options, imports)
            options_block = [f"{indent}    options={options_expr},"]

        bases_block = []
        if operation.bases:
            bases_block = [f"{indent}    bases={operation.bases!r},"]

        lines = [
            f"{indent}ops.CreateModel(",
            f"{indent}    name={operation.name!r},",
            *fields_block,
            *options_block,
            *bases_block,
            f"{indent}),",
        ]
        return lines
