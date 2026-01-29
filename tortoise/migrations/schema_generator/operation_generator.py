from __future__ import annotations

from collections.abc import Iterable, Sequence

from tortoise.migrations.operations import (
    CreateModel,
    DeleteModel,
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

    def generate(self, app_labels: Sequence[str] | None = None) -> list[TortoiseOperation]:
        old_keys = self._filter_keys(self.old_state.models.keys(), app_labels)
        new_keys = self._filter_keys(self.new_state.models.keys(), app_labels)
        renamed_models = self._match_renamed_models(old_keys, new_keys)
        renamed_old_keys = set(renamed_models.values())

        operations: list[TortoiseOperation] = []

        for new_key, old_key in sorted(renamed_models.items()):
            operations.append(RenameModel(old_name=old_key[1], new_name=new_key[1]))

        for new_key in new_keys:
            if new_key in old_keys or new_key in renamed_models:
                continue
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

        return operations
