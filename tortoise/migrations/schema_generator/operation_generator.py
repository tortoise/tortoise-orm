from __future__ import annotations

from collections.abc import Iterable, Sequence

from tortoise.fields.relational import ForeignKeyFieldInstance, ManyToManyFieldInstance
from tortoise.migrations.operations import (
    CreateModel,
    CreateSchema,
    DeleteModel,
    DropSchema,
    RenameModel,
    TortoiseOperation,
)
from tortoise.migrations.schema_generator.state import ModelState, State
from tortoise.migrations.schema_generator.state_diff import StateModelDiff, _model_signature

ModelKey = tuple[str, str]


class OperationGenerator:
    """Generate migration operations by comparing two State snapshots."""

    def __init__(self, old_state: State, new_state: State) -> None:
        self.old_state = old_state
        self.new_state = new_state

    def _filter_keys(
        self, keys: Iterable[ModelKey], app_labels: Sequence[str] | None
    ) -> list[ModelKey]:
        if app_labels is None:
            return sorted(keys)
        app_set = set(app_labels)
        return sorted([key for key in keys if key[0] in app_set])

    def _match_renamed_models(
        self, old_keys: list[ModelKey], new_keys: list[ModelKey]
    ) -> dict[ModelKey, ModelKey]:
        renamed: dict[ModelKey, ModelKey] = {}
        removed_keys = [key for key in old_keys if key not in new_keys]
        added_keys = [key for key in new_keys if key not in old_keys]

        for new_key in added_keys:
            new_state = self.new_state.models[new_key]
            new_sig = _model_signature(new_state)
            for old_key in removed_keys:
                if old_key[0] != new_key[0]:
                    continue
                old_state = self.old_state.models[old_key]
                if new_sig == _model_signature(old_state):
                    renamed[new_key] = old_key
                    removed_keys.remove(old_key)
                    break

        return renamed

    def _create_model_operation(self, model_state: ModelState) -> CreateModel:
        return CreateModel(
            name=model_state.name,
            fields=list(model_state.fields.items()),
            options=model_state.options,
            bases=[base.__name__ for base in model_state.bases],
        )

    @staticmethod
    def _sort_by_dependencies(keys: list[ModelKey], state: State) -> list[ModelKey]:
        """Sort model keys so that FK/M2M dependencies come before dependents."""
        key_set = set(keys)
        # Build adjacency: key -> set of keys it depends on
        deps: dict[ModelKey, set[ModelKey]] = {k: set() for k in keys}
        for key in keys:
            model_state = state.models[key]
            for field in model_state.fields.values():
                if not isinstance(field, (ForeignKeyFieldInstance, ManyToManyFieldInstance)):
                    continue
                ref = getattr(field, "model_name", None)
                if not ref:
                    continue
                if isinstance(ref, str):
                    parts = ref.split(".")
                    if len(parts) == 2:
                        dep_key: ModelKey = (parts[0], parts[1])
                    else:
                        continue
                else:
                    # model_name is a model class
                    dep_key = (getattr(ref._meta, "app", ""), ref.__name__)
                if dep_key in key_set and dep_key != key:
                    deps[key].add(dep_key)

        # Kahn's algorithm
        result: list[ModelKey] = []
        in_degree = {k: len(v) for k, v in deps.items()}
        queue = sorted([k for k, d in in_degree.items() if d == 0])
        while queue:
            node = queue.pop(0)
            result.append(node)
            for k, d in deps.items():
                if node in d:
                    d.discard(node)
                    in_degree[k] -= 1
                    if in_degree[k] == 0:
                        queue.append(k)
                        queue.sort()

        # Append any remaining (circular deps) in sorted order
        remaining = sorted(k for k in keys if k not in result)
        result.extend(remaining)
        return result

    @staticmethod
    def _collect_schemas(state: State) -> set[str]:
        """Collect all unique schema names used in a state."""
        schemas: set[str] = set()
        for model_state in state.models.values():
            schema = model_state.options.get("schema")
            if schema:
                schemas.add(schema)
        return schemas

    def generate(self, app_labels: Sequence[str] | None = None) -> list[TortoiseOperation]:
        old_keys = self._filter_keys(self.old_state.models.keys(), app_labels)
        new_keys = self._filter_keys(self.new_state.models.keys(), app_labels)
        renamed_models = self._match_renamed_models(old_keys, new_keys)
        renamed_old_keys = set(renamed_models.values())

        operations: list[TortoiseOperation] = []

        # Detect new schemas that need creation (before any CreateModel)
        old_schemas = self._collect_schemas(self.old_state)
        new_schemas = self._collect_schemas(self.new_state)
        for schema in sorted(new_schemas - old_schemas):
            operations.append(CreateSchema(schema_name=schema))

        for new_key, old_key in sorted(renamed_models.items()):
            operations.append(RenameModel(old_name=old_key[1], new_name=new_key[1]))

        added_keys = [k for k in new_keys if k not in old_keys and k not in renamed_models]
        for new_key in self._sort_by_dependencies(added_keys, self.new_state):
            operations.append(self._create_model_operation(self.new_state.models[new_key]))

        for new_key in new_keys:
            old_key = renamed_models.get(new_key, new_key)
            if old_key not in self.old_state.models:
                continue
            model_diff = StateModelDiff(
                self.old_state.models[old_key], self.new_state.models[new_key]
            )
            operations.extend(model_diff.generate_operations())

        for old_key in old_keys:
            if old_key in new_keys or old_key in renamed_old_keys:
                continue
            operations.append(DeleteModel(name=old_key[1]))

        # Detect schemas no longer used (after all DeleteModel)
        for schema in sorted(old_schemas - new_schemas):
            operations.append(DropSchema(schema_name=schema))

        return operations
