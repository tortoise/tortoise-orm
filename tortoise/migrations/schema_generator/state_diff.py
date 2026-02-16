from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from tortoise.fields.relational import (
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
)
from tortoise.indexes import Index
from tortoise.migrations.constraints import CheckConstraint, UniqueConstraint
from tortoise.migrations.operations import (
    AddConstraint,
    AddField,
    AddIndex,
    AlterField,
    AlterModelOptions,
    RemoveConstraint,
    RemoveField,
    RemoveIndex,
    RenameConstraint,
    RenameField,
    RenameIndex,
    TortoiseOperation,
)

if TYPE_CHECKING:
    from tortoise.fields.base import Field
    from tortoise.migrations.schema_generator.state import ModelState


# ---------------------------------------------------------------------------
# Shared normalisation helpers
# ---------------------------------------------------------------------------


def _normalize_indexes(value: object) -> list[Index]:
    """Normalise raw index tuples/Index objects into a flat list of Index instances."""
    if not value or not isinstance(value, Iterable):
        return []
    return [item if isinstance(item, Index) else Index(fields=tuple(item)) for item in value]


def _index_signature(index: Index) -> tuple:
    """Return a hashable identity tuple for an Index (ignoring its name)."""
    return (tuple(index.field_names), index.INDEX_TYPE, index.extra)


def _normalize_unique_together(value: object) -> list[tuple[str, ...]]:
    if not value or not isinstance(value, Iterable):
        return []
    return [tuple(fields) for fields in value]


def _normalize_constraints(value: object) -> list[UniqueConstraint | CheckConstraint]:
    if not value or not isinstance(value, Iterable):
        return []
    return [c for c in value if isinstance(c, (UniqueConstraint, CheckConstraint))]


RELATION_FIELDS = (ForeignKeyFieldInstance, OneToOneFieldInstance, ManyToManyFieldInstance)


def _field_signature(field: Field) -> dict[str, object]:
    desc = field.describe(serializable=True)
    if getattr(field, "source_field", None) is None:
        desc.pop("db_column", None)
    for key in ("name", "docstring", "default", "python_type"):
        desc.pop(key, None)
    return desc


def _field_signature_for_rename(field: Field) -> dict[str, object]:
    desc = _field_signature(field)
    desc.pop("source_field", None)
    desc.pop("db_column", None)
    return desc


def _model_options_for_compare(options: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in options.items()
        if key not in ("table", "app", "indexes", "unique_together", "constraints")
    }


def _base_signature(bases: Iterable[type]) -> list[str]:
    return [f"{base.__module__}.{base.__name__}" for base in bases]


def _model_signature(model_state: ModelState) -> dict[str, object]:
    fields = {
        name: _field_signature(field)
        for name, field in model_state.fields.items()
        if not isinstance(field, RELATION_FIELDS)
    }
    return {
        "fields": fields,
        "options": _model_options_for_compare(model_state.options),
        "bases": _base_signature(model_state.bases),
        "pk_field_name": model_state.pk_field_name,
        "abstract": model_state.abstract,
    }


class StateModelDiff:
    def __init__(self, old_state: ModelState, new_state: ModelState) -> None:
        self.old_state = old_state
        self.new_state = new_state

    def generate_operations(self) -> list[TortoiseOperation]:
        if self.old_state == self.new_state:
            return []

        operations: list[TortoiseOperation] = []
        operations.extend(self._generate_index_operations())
        operations.extend(self._generate_constraint_operations())
        old_options = _model_options_for_compare(self.old_state.options)
        new_options = _model_options_for_compare(self.new_state.options)
        if old_options != new_options:
            operations.append(
                AlterModelOptions(
                    name=self.new_state.name,
                    options=self.new_state.options,
                )
            )

        operations.extend(StateFieldDiff(self.old_state, self.new_state).generate_operations())
        return operations

    @staticmethod
    def _normalize_indexes_with_explicit(value: object) -> list[tuple[Index, bool]]:
        """Like _normalize_indexes but tracks whether each item was an explicit Index."""
        if not value or not isinstance(value, Iterable):
            return []
        return [
            (item, True) if isinstance(item, Index) else (Index(fields=tuple(item)), False)
            for item in value
        ]

    def _generate_index_operations(self) -> list[TortoiseOperation]:
        operations: list[TortoiseOperation] = []
        old_indexes = self._normalize_indexes_with_explicit(
            self.old_state.options.get("indexes", ())
        )
        new_indexes = self._normalize_indexes_with_explicit(
            self.new_state.options.get("indexes", ())
        )

        matched_old_indexes: set[int] = set()
        matched_new_indexes: set[int] = set()

        for new_idx, (new_index, new_explicit) in enumerate(new_indexes):
            if not new_explicit or not new_index.name:
                continue
            new_sig = _index_signature(new_index)
            for old_idx, (old_index, old_explicit) in enumerate(old_indexes):
                if old_idx in matched_old_indexes or not old_explicit or not old_index.name:
                    continue
                if new_sig == _index_signature(old_index) and new_index.name != old_index.name:
                    operations.append(
                        RenameIndex(
                            model_name=self.new_state.name,
                            old_name=old_index.name,
                            new_name=new_index.name,
                        )
                    )
                    matched_old_indexes.add(old_idx)
                    matched_new_indexes.add(new_idx)
                    break

        for old_idx, (old_index, _explicit) in enumerate(old_indexes):
            if old_idx in matched_old_indexes:
                continue
            if any(
                _index_signature(old_index) == _index_signature(new_index)
                for new_index, _ in new_indexes
            ):
                continue
            operations.append(
                RemoveIndex(
                    model_name=self.old_state.name,
                    name=old_index.name,
                    fields=list(old_index.field_names) if not old_index.name else None,
                )
            )

        for new_idx, (new_index, _explicit) in enumerate(new_indexes):
            if new_idx in matched_new_indexes:
                continue
            if any(
                _index_signature(new_index) == _index_signature(old_index)
                for old_index, _ in old_indexes
            ):
                continue
            operations.append(AddIndex(model_name=self.new_state.name, index=new_index))

        return operations

    def _generate_constraint_operations(self) -> list[TortoiseOperation]:
        operations: list[TortoiseOperation] = []
        old_unique = _normalize_unique_together(self.old_state.options.get("unique_together", ()))
        new_unique = _normalize_unique_together(self.new_state.options.get("unique_together", ()))

        for fields in old_unique:
            if fields not in new_unique:
                operations.append(
                    RemoveConstraint(
                        model_name=self.old_state.name,
                        fields=list(fields),
                    )
                )

        for fields in new_unique:
            if fields not in old_unique:
                operations.append(
                    AddConstraint(
                        model_name=self.new_state.name,
                        constraint=UniqueConstraint(fields=tuple(fields)),
                    )
                )

        old_constraints = _normalize_constraints(self.old_state.options.get("constraints", ()))
        new_constraints = _normalize_constraints(self.new_state.options.get("constraints", ()))

        # Rename detection for UniqueConstraint (by matching fields)
        old_by_fields = {
            tuple(constraint.fields): constraint
            for constraint in old_constraints
            if isinstance(constraint, UniqueConstraint) and constraint.name
        }
        new_by_fields = {
            tuple(constraint.fields): constraint
            for constraint in new_constraints
            if isinstance(constraint, UniqueConstraint) and constraint.name
        }

        for fields, new_constraint in new_by_fields.items():
            old_constraint = old_by_fields.get(fields)
            if (
                old_constraint
                and old_constraint.name is not None
                and new_constraint.name is not None
                and old_constraint.name != new_constraint.name
            ):
                operations.append(
                    RenameConstraint(
                        model_name=self.new_state.name,
                        old_name=old_constraint.name,
                        new_name=new_constraint.name,
                    )
                )

        # Rename detection for CheckConstraint (by matching check expression)
        old_by_check: dict[str, CheckConstraint] = {
            constraint.check: constraint
            for constraint in old_constraints
            if isinstance(constraint, CheckConstraint)
        }
        new_by_check: dict[str, CheckConstraint] = {
            constraint.check: constraint
            for constraint in new_constraints
            if isinstance(constraint, CheckConstraint)
        }

        for check_expr, new_ck in new_by_check.items():
            old_ck = old_by_check.get(check_expr)
            if old_ck and old_ck.name != new_ck.name:
                operations.append(
                    RenameConstraint(
                        model_name=self.new_state.name,
                        old_name=old_ck.name,
                        new_name=new_ck.name,
                    )
                )

        for constraint in old_constraints:
            if constraint.name and any(
                op
                for op in operations
                if isinstance(op, RenameConstraint) and op.old_name == constraint.name
            ):
                continue
            if constraint not in new_constraints:
                operations.append(
                    RemoveConstraint(
                        model_name=self.old_state.name,
                        name=constraint.name,
                    )
                )

        for constraint in new_constraints:
            if constraint.name and any(
                op
                for op in operations
                if isinstance(op, RenameConstraint) and op.new_name == constraint.name
            ):
                continue
            if constraint not in old_constraints:
                operations.append(
                    AddConstraint(
                        model_name=self.new_state.name,
                        constraint=constraint,
                    )
                )

        return operations


class StateFieldDiff:
    def __init__(self, old_state: ModelState, new_state: ModelState) -> None:
        self.old_state = old_state
        self.new_state = new_state

    def _generated_field_recreate_ops(
        self, field_name: str, field: Field
    ) -> list[TortoiseOperation]:
        operations: list[TortoiseOperation] = []
        if getattr(field, "index", False):
            operations.append(
                AddIndex(model_name=self.new_state.name, index=Index(fields=(field_name,)))
            )

        old_indexes = _normalize_indexes(self.old_state.options.get("indexes", ()))
        new_indexes = _normalize_indexes(self.new_state.options.get("indexes", ()))
        old_index_sigs = {_index_signature(index) for index in old_indexes}
        for index in new_indexes:
            if _index_signature(index) not in old_index_sigs:
                continue
            if index.fields and field_name in index.fields:
                operations.append(AddIndex(model_name=self.new_state.name, index=index))

        old_unique = set(
            _normalize_unique_together(self.old_state.options.get("unique_together", ()))
        )
        new_unique = set(
            _normalize_unique_together(self.new_state.options.get("unique_together", ()))
        )
        for fields in new_unique & old_unique:
            if field_name not in fields:
                continue
            operations.append(
                AddConstraint(
                    model_name=self.new_state.name,
                    constraint=UniqueConstraint(fields=tuple(fields)),
                )
            )

        old_constraints = _normalize_constraints(self.old_state.options.get("constraints", ()))
        new_constraints = _normalize_constraints(self.new_state.options.get("constraints", ()))
        old_constraints_set = set(old_constraints)
        for constraint in new_constraints:
            if constraint not in old_constraints_set:
                continue
            if isinstance(constraint, UniqueConstraint) and field_name in constraint.fields:
                operations.append(
                    AddConstraint(model_name=self.new_state.name, constraint=constraint)
                )

        return operations

    def generate_operations(self) -> list[TortoiseOperation]:
        operations: list[TortoiseOperation] = []
        old_fields = self.old_state.fields
        new_fields = self.new_state.fields
        added_fields = set(new_fields) - set(old_fields)
        removed_fields = set(old_fields) - set(new_fields)

        for new_name in sorted(added_fields):
            new_sig = _field_signature_for_rename(new_fields[new_name])
            for old_name in sorted(removed_fields):
                if new_sig == _field_signature_for_rename(old_fields[old_name]):
                    operations.append(
                        RenameField(
                            model_name=self.new_state.name,
                            old_name=old_name,
                            new_name=new_name,
                        )
                    )
                    removed_fields.remove(old_name)
                    added_fields.remove(new_name)
                    break

        for name in sorted(set(old_fields) & set(new_fields)):
            old_sig = _field_signature(old_fields[name])
            new_sig = _field_signature(new_fields[name])
            if old_sig != new_sig:
                old_field = old_fields[name]
                new_field = new_fields[name]
                if old_field.generated or new_field.generated:
                    operations.append(RemoveField(model_name=self.new_state.name, name=name))
                    operations.append(
                        AddField(model_name=self.new_state.name, name=name, field=new_field)
                    )
                    operations.extend(self._generated_field_recreate_ops(name, new_field))
                else:
                    operations.append(
                        AlterField(model_name=self.new_state.name, name=name, field=new_field)
                    )

        for name in sorted(added_fields):
            operations.append(
                AddField(model_name=self.new_state.name, name=name, field=new_fields[name])
            )

        for name in sorted(removed_fields):
            operations.append(RemoveField(model_name=self.new_state.name, name=name))

        return operations
