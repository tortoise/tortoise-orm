from typing import List, Any, Dict, Tuple, Type, Optional, cast

from tortoise import (
    BaseDBAsyncClient,
    Model,
    Tortoise,
    ForeignKeyFieldInstance,
    OneToOneFieldInstance,
    ManyToManyFieldInstance,
)
from tortoise.fields import Field
from tortoise.fields.relational import RelationalField
from tortoise.migrations.exceptions import IncompatibleStateError
from tortoise.migrations.schema_editor.base import BaseSchemaEditor
from tortoise.migrations.schema_generator.state import State, ModelState

DIRECT_RELATION_FIELDS = (
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
)


class Operation:
    async def run(
        self,
        app_label: str,
        state: "State",
        dry_run: bool,
        state_editor: BaseSchemaEditor = None,
    ):
        raise NotImplementedError()


class SQLOperation(Operation):
    def __init__(self, query: str, values: List[Any]):
        self.query = query
        self.values = values

    async def run(
        self,
        app_label: str,
        state: "State",
        dry_run: bool,
        state_editor: BaseSchemaEditor = None,
    ):
        if not dry_run:
            await state_editor.client.execute_query_dict(self.query, self.values)


class TortoiseOperation(Operation):
    def state_forward(self, app_label: str, state: "State"):
        return

    @staticmethod
    def get_model_state(state: "State", app_label: str, model_name: str) -> ModelState:
        model = state.models.get((app_label, model_name))
        if not model:
            raise IncompatibleStateError()

        return model

    async def database_forward(self, old_state: State, new_state: State, state_editor: BaseSchemaEditor = None):
        return

    async def database_backward(self, old_state: State, new_state: State, state_editor: BaseSchemaEditor = None):
        return

    async def run(
        self,
        app_label: str,
        state: "State",
        dry_run: bool,
        state_editor: BaseSchemaEditor = None,
    ):
        self.state_forward(app_label, state)


class CreateModel(TortoiseOperation):
    def __init__(
        self,
        name: str,
        fields: List[Tuple[str, Field]],
        options: Dict[str, Any] = None,
        bases: List[str] = None,
    ):
        self.options = options
        self.fields = fields
        self.name = name
        self.bases = bases
        self._model: Optional[Type[Model]] = None

    @property
    def model(self) -> Type[Model]:
        if not self._model:
            meta_class = type("Meta", (), self.options or {})

            attributes = dict(self.fields)
            attributes["Meta"] = meta_class
            # TODO work with actual bases
            self._model = cast(Type[Model], type(self.name, (Model,), attributes))
            self._model._meta.finalise_fields()
            self._model._meta.finalise_pk()

        return self._model

    def state_forward(self, app_label: str, state: "State"):
        model_state = ModelState.make_from_model(app_label, self.model)
        state.models[(app_label, self.name)] = model_state

        models_to_reload = {(app_label, self.name)}

        for field in model_state.fields.values():
            if not isinstance(field, DIRECT_RELATION_FIELDS,):
                continue

            models_to_reload.add(state.apps.split_reference(field.model_name))

        state.reload_models(models_to_reload)

    async def run_sql(self, db_connection: BaseDBAsyncClient = None):
        pass


class RenameModel(TortoiseOperation):
    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name

    def state_forward(self, app_label: str, state: "State"):
        model_state_to_change = state.models.pop((app_label, self.old_name), None)
        if not model_state_to_change:
            raise IncompatibleStateError()

        model_state_to_change.name = self.new_name
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
                    _, field_args, field_kwargs = field.deconstruct()
                    field_kwargs["model_name"] = new_model_reference
                    new_field = field.__class__(*field_args, **field_kwargs)
                    model_state.fields[field_name] = new_field

        state.reload_model(app_label, self.new_name)


class DeleteModel(TortoiseOperation):
    def __init__(self, name: str):
        self.name = name

    def state_forward(self, app_label: str, state: "State"):
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


class AlterModelOptions(TortoiseOperation):
    def __init__(self, name: str, options: Dict[str, Any]):
        self.name = name
        self.options = options

    def state_forward(self, app_label: str, state: "State"):
        model_state = self.get_model_state(state, app_label, self.name)

        model_state.options.update(self.options)
        state.reload_model(app_label, self.name)


class AddField(TortoiseOperation):
    def __init__(self, model_name: str, name: str, field: Field):
        self.model_name = model_name
        self.name = name
        self.field = field

    def state_forward(self, app_label: str, state: "State"):
        model_state = self.get_model_state(state, app_label, self.model_name)

        if self.name in model_state.fields:
            raise IncompatibleStateError(
                f"Field {self.name} already present on model {app_label}.{self.model_name}"
            )

        # TODO Foreign key key fields add/remove
        model_state.fields[self.name] = self.field.clone()
        models_to_reload = {(app_label, self.model_name)}

        if isinstance(self.field, DIRECT_RELATION_FIELDS):
            models_to_reload.add(state.apps.split_reference(self.field.model_name))

        state.reload_models(models_to_reload)


class RemoveField(TortoiseOperation):
    def __init__(self, model_name: str, name: str):
        self.model_name = model_name
        self.name = name

    def state_forward(self, app_label: str, state: "State"):
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


class AlterField(TortoiseOperation):
    def __init__(self, model_name: str, name: str, field: Field):
        self.model_name = model_name
        self.name = name
        self.field = field

    def state_forward(self, app_label: str, state: "State"):
        model_state = self.get_model_state(state, app_label, self.model_name)

        if self.name not in model_state.fields:
            raise IncompatibleStateError(f"Field {self.name} is not present on model {app_label}.{self.model_name}")

        model_state.fields[self.name] = self.field
        models_to_reload = {(app_label, self.model_name)}
        if isinstance(self.field, DIRECT_RELATION_FIELDS):
            models_to_reload.add(state.apps.split_reference(self.field.model_name))

        state.reload_models(models_to_reload)
