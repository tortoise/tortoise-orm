from __future__ import annotations

import inspect
from copy import deepcopy
from typing import TYPE_CHECKING, Any, TypeAlias, cast

from tortoise import BaseDBAsyncClient, Model
from tortoise.fields import Field
from tortoise.fields.relational import (
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
)
from tortoise.indexes import Index
from tortoise.migrations.constraints import UniqueConstraint
from tortoise.migrations.exceptions import IncompatibleStateError
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_generator.state import ModelState, State
from tortoise.migrations.schema_generator.state_apps import StateApps

if TYPE_CHECKING:
    from tortoise.fields.base import Field as BaseField
    from tortoise.fields.relational import ManyToManyRelation

    FieldLike: TypeAlias = BaseField[Any] | ManyToManyRelation[Any] | None
else:
    FieldLike = Field

DIRECT_RELATION_FIELDS = (
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
)


class Operation:
    reversible = True
    reduces_to_sql = True
    atomic: bool | None = False

    def describe(self) -> str:
        return self.__class__.__name__

    async def run(
        self,
        app_label: str,
        state: State,
        dry_run: bool,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        raise NotImplementedError()

    def state_forward(self, app_label: str, state: State) -> None:
        raise NotImplementedError()

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        raise NotImplementedError()

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        raise NotImplementedError()


class SQLOperation(Operation):
    def __init__(self, query: str, values: list[Any]):
        self.query = query
        self.values = values

    async def run(
        self,
        app_label: str,
        state: State,
        dry_run: bool,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not dry_run and state_editor:
            if self.values:
                if state_editor.collect_sql:
                    state_editor.collected_sql.append(f"{self.query}  -- params: {self.values!r}")
                else:
                    await state_editor.client.execute_query_dict(self.query, self.values)
            else:
                await state_editor._run_sql(self.query)


class TortoiseOperation(Operation):
    def state_forward(self, app_label: str, state: State) -> None:
        return None

    @staticmethod
    def get_model_state(state: State, app_label: str, model_name: str) -> ModelState:
        model = state.models.get((app_label, model_name))
        if not model:
            raise IncompatibleStateError()

        return model

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        return None

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        return None

    async def run(
        self,
        app_label: str,
        state: State,
        dry_run: bool,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        old_state = state.clone() if (not dry_run and state_editor) else None
        self.state_forward(app_label, state)
        if dry_run or not state_editor:
            return
        await self.database_forward(app_label, old_state, state, state_editor)  # type: ignore[arg-type]


class CreateModel(TortoiseOperation):
    def __init__(
        self,
        name: str,
        fields: list[tuple[str, FieldLike]],
        options: dict[str, Any] | None = None,
        bases: list[str] | None = None,
    ) -> None:
        self.options = options
        self.fields = fields
        self.name = name
        self.bases = bases
        self._model: type[Model] | None = None

    def describe(self) -> str:
        return f"Create model {self.name}"

    @property
    def model(self) -> type[Model]:
        if not self._model:
            meta_class = type("Meta", (), self.options or {})

            attributes: dict[str, Any] = dict(self.fields)
            attributes["Meta"] = meta_class
            attributes["_no_comments"] = True
            self._model = cast(type[Model], type(self.name, (Model,), attributes))

        return self._model

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = ModelState.make_from_model(app_label, self.model)
        state.models[(app_label, self.name)] = model_state

        models_to_reload = {(app_label, self.name)}

        for field in model_state.fields.values():
            if not isinstance(field, DIRECT_RELATION_FIELDS):
                continue

            related_key = state.apps.split_reference(field.model_name)
            if related_key in state.models:
                models_to_reload.add(related_key)

        # Also find existing models that reference the newly created model.
        # This handles the case where a model with a FK was created before its
        # target (e.g. alphabetical ordering: Alert before Warehouse).
        new_model_ref = f"{app_label}.{self.name}"
        for key, existing_state in state.models.items():
            if key == (app_label, self.name):
                continue
            for field in existing_state.fields.values():
                if isinstance(field, DIRECT_RELATION_FIELDS) and field.model_name == new_model_ref:
                    models_to_reload.add(key)
                    break

        state.reload_models(models_to_reload)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.name}")
        await state_editor.create_model(model)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.name}")
        await state_editor.delete_model(model)

    async def run_sql(self, db_connection: BaseDBAsyncClient | None = None) -> None:
        return None


class RenameModel(TortoiseOperation):
    def __init__(self, old_name: str, new_name: str) -> None:
        self.old_name = old_name
        self.new_name = new_name

    def describe(self) -> str:
        return f"Rename model {self.old_name} to {self.new_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state_to_change = state.models.pop((app_label, self.old_name), None)
        if not model_state_to_change:
            raise IncompatibleStateError()

        state.apps.unregister_model(app_label, self.old_name)

        old_table = model_state_to_change.table
        model_state_to_change.name = self.new_name
        if old_table == self.old_name.lower():
            model_state_to_change.table = self.new_name.lower()
            if model_state_to_change.options.get("table") == old_table:
                model_state_to_change.options["table"] = model_state_to_change.table
        state.models[(app_label, self.new_name)] = model_state_to_change
        old_model_reference = f"{app_label}.{self.old_name}"
        new_model_reference = f"{app_label}.{self.new_name}"

        for model_state in state.models.values():
            for field_name, field in model_state.fields.items():
                if not isinstance(
                    field,
                    (
                        ForeignKeyFieldInstance,
                        OneToOneFieldInstance,
                        ManyToManyFieldInstance,
                    ),
                ):
                    continue

                if field.model_name == old_model_reference:
                    new_field = deepcopy(field)
                    new_field.model_name = new_model_reference
                    model_state.fields[field_name] = new_field

        state.reload_model(app_label, self.new_name)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        old_model = old_state.apps.get_model(f"{app_label}.{self.old_name}")
        new_model = new_state.apps.get_model(f"{app_label}.{self.new_name}")
        old_table = old_model._meta.db_table
        new_table = new_model._meta.db_table
        if old_table == new_table:
            return
        await state_editor.rename_table(new_model, old_table, new_table)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        old_model = old_state.apps.get_model(f"{app_label}.{self.new_name}")
        new_model = new_state.apps.get_model(f"{app_label}.{self.old_name}")
        old_table = old_model._meta.db_table
        new_table = new_model._meta.db_table
        if old_table == new_table:
            return
        await state_editor.rename_table(new_model, old_table, new_table)


class DeleteModel(TortoiseOperation):
    def __init__(self, name: str) -> None:
        self.name = name

    def describe(self) -> str:
        return f"Delete model {self.name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_ref = f"{app_label}.{self.name}"

        for model_state in state.models.values():
            for field_name, field in model_state.fields.items():
                if not isinstance(field, DIRECT_RELATION_FIELDS):
                    continue

                if field.model_name == model_ref:
                    raise IncompatibleStateError(
                        f"{model_ref} is still referenced from {model_state.app}.{model_state.name}"
                    )

        model_state_to_delete = state.models.pop((app_label, self.name), None)
        if not model_state_to_delete:
            raise IncompatibleStateError()

        models_to_reload = set()

        for field in model_state_to_delete.fields.values():
            if not isinstance(field, DIRECT_RELATION_FIELDS):
                continue

            models_to_reload.add(state.apps.split_reference(field.model_name))

        state.reload_models(models_to_reload)
        state.apps.unregister_model(app_label, self.name)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.name}")
        await state_editor.delete_model(model)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.name}")
        await state_editor.create_model(model)


class AlterModelOptions(TortoiseOperation):
    def __init__(self, name: str, options: dict[str, Any]):
        self.name = name
        self.options = options

    def describe(self) -> str:
        return f"Alter options for {self.name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.name)

        model_state.options.update(self.options)
        state.reload_model(app_label, self.name)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        return None

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        return None


class AddField(TortoiseOperation):
    def __init__(self, model_name: str, name: str, field: FieldLike) -> None:
        self.model_name = model_name
        self.name = name
        self.field = field

    def describe(self) -> str:
        return f"Add field {self.name} to {self.model_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)

        if self.name in model_state.fields:
            raise IncompatibleStateError(
                f"Field {self.name} already present on model {app_label}.{self.model_name}"
            )

        model_state.fields[self.name] = cast(Field, deepcopy(self.field))
        models_to_reload = {(app_label, self.model_name)}

        if isinstance(self.field, DIRECT_RELATION_FIELDS):
            models_to_reload.add(state.apps.split_reference(self.field.model_name))

        state.reload_models(models_to_reload)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        await state_editor.add_field(model, self.name)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        field = model._meta.fields_map[self.name]
        await state_editor.remove_field(model, field)


class RemoveField(TortoiseOperation):
    def __init__(self, model_name: str, name: str) -> None:
        self.model_name = model_name
        self.name = name

    def describe(self) -> str:
        return f"Remove field {self.name} from {self.model_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)

        field = model_state.fields.pop(self.name, None)
        if not field:
            raise IncompatibleStateError(
                f"Field {field} is not present on model {app_label}.{self.model_name}"
            )

        models_to_reload = {(app_label, self.model_name)}
        if isinstance(field, DIRECT_RELATION_FIELDS):
            models_to_reload.add(state.apps.split_reference(field.model_name))

        state.reload_models(models_to_reload)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        field = model._meta.fields_map[self.name]
        await state_editor.remove_field(model, field)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        await state_editor.add_field(model, self.name)


class AlterField(TortoiseOperation):
    def __init__(self, model_name: str, name: str, field: FieldLike) -> None:
        self.model_name = model_name
        self.name = name
        self.field = field

    def describe(self) -> str:
        return f"Alter field {self.name} on {self.model_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)

        if self.name not in model_state.fields:
            raise IncompatibleStateError(
                f"Field {self.name} is not present on model {app_label}.{self.model_name}"
            )

        model_state.fields[self.name] = cast(Field, deepcopy(self.field))
        models_to_reload = {(app_label, self.model_name)}
        if isinstance(self.field, DIRECT_RELATION_FIELDS):
            models_to_reload.add(state.apps.split_reference(self.field.model_name))

        state.reload_models(models_to_reload)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        old_model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        new_model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        await state_editor.alter_field(old_model, new_model, self.name)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        old_model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        new_model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        await state_editor.alter_field(old_model, new_model, self.name)


class RenameField(TortoiseOperation):
    def __init__(self, model_name: str, old_name: str, new_name: str) -> None:
        self.model_name = model_name
        self.old_name = old_name
        self.new_name = new_name

    def describe(self) -> str:
        return f"Rename field {self.old_name} to {self.new_name} on {self.model_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)

        if self.new_name in model_state.fields:
            raise IncompatibleStateError(
                f"Field {self.new_name} already present on model {app_label}.{self.model_name}"
            )

        field = model_state.fields.pop(self.old_name, None)
        if not field:
            raise IncompatibleStateError(
                f"Field {self.old_name} is not present on model {app_label}.{self.model_name}"
            )

        model_state.fields[self.new_name] = deepcopy(field)
        models_to_reload = {(app_label, self.model_name)}
        if isinstance(field, DIRECT_RELATION_FIELDS):
            models_to_reload.add(state.apps.split_reference(field.model_name))

        state.reload_models(models_to_reload)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        old_model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        new_model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        old_field = old_model._meta.fields_map[self.old_name]
        new_field = new_model._meta.fields_map[self.new_name]
        old_db_field = old_field.source_field or old_field.model_field_name
        new_db_field = new_field.source_field or new_field.model_field_name
        if old_db_field == new_db_field:
            return
        await state_editor._run_sql(
            state_editor.RENAME_FIELD_TEMPLATE.format(
                table=new_model._meta.db_table,
                old_column=old_db_field,
                new_column=new_db_field,
            )
        )

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        old_model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        new_model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        old_field = old_model._meta.fields_map[self.new_name]
        new_field = new_model._meta.fields_map[self.old_name]
        old_db_field = old_field.source_field or old_field.model_field_name
        new_db_field = new_field.source_field or new_field.model_field_name
        if old_db_field == new_db_field:
            return
        await state_editor._run_sql(
            state_editor.RENAME_FIELD_TEMPLATE.format(
                table=new_model._meta.db_table,
                old_column=old_db_field,
                new_column=new_db_field,
            )
        )


def _get_option_list(model_state: ModelState, key: str) -> list:
    value = model_state.options.get(key)
    if not value:
        return []
    if isinstance(value, tuple):
        return list(value)
    return list(value)


def _set_option_list(model_state: ModelState, key: str, values: list) -> None:
    if values:
        model_state.options[key] = tuple(values)
    else:
        model_state.options.pop(key, None)


class AddIndex(TortoiseOperation):
    def __init__(self, model_name: str, index: Index) -> None:
        self.model_name = model_name
        self.index = index

    def describe(self) -> str:
        return f"Add index to {self.model_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)
        indexes = _get_option_list(model_state, "indexes")
        indexes.append(self.index)
        _set_option_list(model_state, "indexes", indexes)
        state.reload_model(app_label, self.model_name)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        await state_editor.add_index(model, self.index)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        await state_editor.remove_index(model, self.index)


class RemoveIndex(TortoiseOperation):
    def __init__(
        self, model_name: str, name: str | None = None, fields: list[str] | None = None
    ) -> None:
        if not name and not fields:
            raise ValueError("RemoveIndex requires name or fields.")
        self.model_name = model_name
        self.name = name
        self.fields = fields

    def describe(self) -> str:
        return f"Remove index from {self.model_name}"

    def _find_index(self, model_state: ModelState) -> Index:
        indexes = _get_option_list(model_state, "indexes")
        if self.name:
            for index in indexes:
                if isinstance(index, Index) and index.name == self.name:
                    return index
        if self.fields:
            for index in indexes:
                if isinstance(index, Index) and list(index.field_names) == list(self.fields):
                    return index
                if not isinstance(index, Index) and list(index) == list(self.fields):
                    return Index(fields=tuple(self.fields))
        raise IncompatibleStateError(
            f"Index {self.name or self.fields} is not present on {self.model_name}"
        )

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)
        indexes = _get_option_list(model_state, "indexes")
        index = self._find_index(model_state)
        indexes.remove(index)
        _set_option_list(model_state, "indexes", indexes)
        state.reload_model(app_label, self.model_name)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        model_state = old_state.models[(app_label, self.model_name)]
        index = self._find_index(model_state)
        await state_editor.remove_index(model, index)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        model_state = new_state.models[(app_label, self.model_name)]
        index = self._find_index(model_state)
        await state_editor.add_index(model, index)


class RenameIndex(TortoiseOperation):
    def __init__(
        self,
        model_name: str,
        new_name: str,
        *,
        old_name: str | None = None,
        old_fields: list[str] | None = None,
    ) -> None:
        if not old_name and not old_fields:
            raise ValueError("RenameIndex requires old_name or old_fields.")
        if old_name and old_fields:
            raise ValueError("RenameIndex.old_name and old_fields are mutually exclusive.")
        self.model_name = model_name
        self.new_name = new_name
        self.old_name = old_name
        self.old_fields = old_fields

    def describe(self) -> str:
        return f"Rename index on {self.model_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)
        indexes = _get_option_list(model_state, "indexes")
        if self.old_fields:
            for index in list(indexes):
                if isinstance(index, Index) and list(index.field_names) == list(self.old_fields):
                    indexes.remove(index)
                elif not isinstance(index, Index) and list(index) == list(self.old_fields):
                    indexes.remove(index)
            indexes.append(Index(fields=tuple(self.old_fields), name=self.new_name))
            _set_option_list(model_state, "indexes", indexes)
            state.reload_model(app_label, self.model_name)
            return
        for index in indexes:
            if isinstance(index, Index) and index.name == self.old_name:
                indexes.remove(index)
                indexes.append(Index(fields=tuple(index.field_names), name=self.new_name))
                break
        else:
            raise IncompatibleStateError(
                f"Index {self.old_name} is not present on {self.model_name}"
            )
        _set_option_list(model_state, "indexes", indexes)
        state.reload_model(app_label, self.model_name)

    def _resolve_old_index(self, model_state: ModelState) -> Index:
        if self.old_name:
            for index in _get_option_list(model_state, "indexes"):
                if isinstance(index, Index) and index.name == self.old_name:
                    return index
        if self.old_fields:
            return Index(fields=tuple(self.old_fields), name=self.old_name)
        raise IncompatibleStateError()

    def _resolve_new_index(self, model_state: ModelState) -> Index:
        for index in _get_option_list(model_state, "indexes"):
            if isinstance(index, Index) and index.name == self.new_name:
                return index
        raise IncompatibleStateError()

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        old_index = self._resolve_old_index(old_state.models[(app_label, self.model_name)])
        new_index = self._resolve_new_index(new_state.models[(app_label, self.model_name)])
        await state_editor.rename_index(model, old_index, new_index)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        old_index = self._resolve_new_index(old_state.models[(app_label, self.model_name)])
        new_index = self._resolve_old_index(new_state.models[(app_label, self.model_name)])
        await state_editor.rename_index(model, old_index, new_index)


class AddConstraint(TortoiseOperation):
    def __init__(self, model_name: str, constraint: UniqueConstraint) -> None:
        self.model_name = model_name
        self.constraint = constraint

    def describe(self) -> str:
        return f"Add constraint to {self.model_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)
        if self.constraint.name:
            constraints = _get_option_list(model_state, "constraints")
            constraints.append(self.constraint)
            _set_option_list(model_state, "constraints", constraints)
        else:
            unique_together = _get_option_list(model_state, "unique_together")
            unique_together.append(self.constraint.fields)
            _set_option_list(model_state, "unique_together", unique_together)
        state.reload_model(app_label, self.model_name)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        await state_editor.add_constraint(model, self.constraint)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        await state_editor.remove_constraint(model, self.constraint)


class RemoveConstraint(TortoiseOperation):
    def __init__(self, model_name: str, name: str | None = None, fields: list[str] | None = None):
        if not name and not fields:
            raise ValueError("RemoveConstraint requires name or fields.")
        self.model_name = model_name
        self.name = name
        self.fields = fields

    def describe(self) -> str:
        return f"Remove constraint from {self.model_name}"

    def _resolve_constraint(self, model_state: ModelState) -> UniqueConstraint:
        if self.name:
            for constraint in _get_option_list(model_state, "constraints"):
                if isinstance(constraint, UniqueConstraint) and constraint.name == self.name:
                    return constraint
        if self.fields:
            for fields in _get_option_list(model_state, "unique_together"):
                if tuple(fields) == tuple(self.fields):
                    return UniqueConstraint(tuple(self.fields))
        raise IncompatibleStateError(
            f"Constraint {self.name or self.fields} is not present on {self.model_name}"
        )

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)
        if self.name:
            constraints = _get_option_list(model_state, "constraints")
            constraints = [
                constraint
                for constraint in constraints
                if not (isinstance(constraint, UniqueConstraint) and constraint.name == self.name)
            ]
            _set_option_list(model_state, "constraints", constraints)
        if self.fields:
            unique_together = _get_option_list(model_state, "unique_together")
            unique_together = [
                fields for fields in unique_together if tuple(fields) != tuple(self.fields)
            ]
            _set_option_list(model_state, "unique_together", unique_together)
        state.reload_model(app_label, self.model_name)

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = old_state.apps.get_model(f"{app_label}.{self.model_name}")
        model_state = old_state.models[(app_label, self.model_name)]
        constraint = self._resolve_constraint(model_state)
        await state_editor.remove_constraint(model, constraint)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        model_state = new_state.models[(app_label, self.model_name)]
        constraint = self._resolve_constraint(model_state)
        await state_editor.add_constraint(model, constraint)


class RenameConstraint(TortoiseOperation):
    def __init__(self, model_name: str, old_name: str, new_name: str) -> None:
        self.model_name = model_name
        self.old_name = old_name
        self.new_name = new_name

    def describe(self) -> str:
        return f"Rename constraint on {self.model_name}"

    def state_forward(self, app_label: str, state: State) -> None:
        model_state = self.get_model_state(state, app_label, self.model_name)
        constraints = _get_option_list(model_state, "constraints")
        for constraint in constraints:
            if isinstance(constraint, UniqueConstraint) and constraint.name == self.old_name:
                constraints.remove(constraint)
                constraints.append(UniqueConstraint(fields=constraint.fields, name=self.new_name))
                _set_option_list(model_state, "constraints", constraints)
                state.reload_model(app_label, self.model_name)
                return
        raise IncompatibleStateError(
            f"Constraint {self.old_name} is not present on {self.model_name}"
        )

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        old_constraint = UniqueConstraint(fields=(), name=self.old_name)
        new_constraint = UniqueConstraint(fields=(), name=self.new_name)
        await state_editor.rename_constraint(model, old_constraint, new_constraint)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        model = new_state.apps.get_model(f"{app_label}.{self.model_name}")
        old_constraint = UniqueConstraint(fields=(), name=self.new_name)
        new_constraint = UniqueConstraint(fields=(), name=self.old_name)
        await state_editor.rename_constraint(model, old_constraint, new_constraint)


class RunPython(TortoiseOperation):
    reduces_to_sql = False

    def __init__(
        self,
        code,
        reverse_code=None,
        *,
        atomic: bool | None = None,
    ) -> None:
        if not callable(code):
            raise ValueError("RunPython must be supplied with a callable")
        if reverse_code is not None and not callable(reverse_code):
            raise ValueError("RunPython must be supplied with callable arguments")
        self.code = code
        self.reverse_code = reverse_code
        self.atomic = atomic
        self.reversible = reverse_code is not None

    def describe(self) -> str:
        return "Run Python code"

    def state_forward(self, app_label: str, state: State) -> None:
        return None

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        result = self.code(old_state.apps, state_editor)
        if inspect.isawaitable(result):
            await result

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        if self.reverse_code is None:
            raise NotImplementedError("RunPython reverse_code is not set")
        result = self.reverse_code(old_state.apps, state_editor)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def noop(apps: StateApps, schema_editor: BaseSchemaEditor) -> None:
        return None


class RunSQL(TortoiseOperation):
    """
    Run raw SQL statements. Optionally provide reverse SQL for rollback.

    Supports:
    - Single SQL string
    - List/tuple of SQL strings
    - List/tuple of (sql, params) tuples for parameterized queries
    """

    reduces_to_sql = True
    noop = ""

    def __init__(
        self,
        sql,
        reverse_sql=None,
        *,
        atomic: bool | None = None,
    ) -> None:
        self.sql = sql
        self.reverse_sql = reverse_sql
        self.atomic = atomic
        self.reversible = reverse_sql is not None

    def describe(self) -> str:
        return "Run SQL"

    def state_forward(self, app_label: str, state: State) -> None:
        return None

    async def database_forward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        await self._run_sql(state_editor, self.sql)

    async def database_backward(
        self,
        app_label: str,
        old_state: State,
        new_state: State,
        state_editor: BaseSchemaEditor | None = None,
    ) -> None:
        if not state_editor:
            return
        if self.reverse_sql is None:
            raise NotImplementedError("RunSQL reverse_sql is not set")
        await self._run_sql(state_editor, self.reverse_sql)

    async def _run_sql(self, state_editor: BaseSchemaEditor, sqls) -> None:
        """Execute SQL statements using the schema editor."""
        if isinstance(sqls, (list, tuple)):
            for sql in sqls:
                params = None
                if isinstance(sql, (list, tuple)):
                    elements = len(sql)
                    if elements == 2:
                        sql, params = sql
                    else:
                        raise ValueError(f"Expected a 2-tuple but got {elements}")

                if params:
                    if state_editor.collect_sql:
                        state_editor.collected_sql.append(f"{sql}  -- params: {params!r}")
                    else:
                        await state_editor.client.execute_query(sql, params)
                else:
                    await state_editor._run_sql(sql)
        elif sqls != RunSQL.noop:
            await state_editor._run_sql(sqls)
