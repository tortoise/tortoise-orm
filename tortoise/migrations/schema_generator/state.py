import inspect
from dataclasses import dataclass
from typing import List, Dict, Any, Type, Tuple, cast, Set, Iterable

from tortoise import Apps, Model
from tortoise.fields.base import Field
from tortoise.fields.relational import (
    RelationalField,
    BackwardFKRelation,
    ManyToManyFieldInstance,
)
from tortoise.migrations.schema_generator.state_apps import StateApps


@dataclass
class BaseEntityState:
    @classmethod
    def from_dict(cls, env) -> "BaseEntityState":
        return cls(
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )


@dataclass
class ModelState(BaseEntityState):
    name: str
    app: str
    table: str
    abstract: bool
    description: str
    options: Dict[str, Any]
    bases: Tuple[type, ...]
    pk_field_name: str
    fields: Dict[str, Field]

    def clone(self) -> "ModelState":
        return self.__class__(
            name=self.name,
            app=self.app,
            table=self.table,
            abstract=self.abstract,
            description=self.description,
            options=dict(self.options),
            bases=self.bases,
            pk_field_name=self.pk_field_name,
            fields={name: field.clone() for name, field in self.fields.items()},
        )

    def render(self, apps: Apps) -> Type[Model]:
        meta_class = type("Meta", (), self.options)

        attrs = {name: field.clone() for name, field in self.fields.items()}
        attrs["Meta"] = meta_class

        model = type(self.name, self.bases, attrs)
        model = cast(Type[Model], model)
        model._meta.finalise_fields()
        model._meta.finalise_pk()
        return model

    @classmethod
    def make_from_model(cls, app_label: str, model: Type[Model]) -> "ModelState":
        # TODO consider removing app_label from make_from_model
        fields = {}

        # Ignore backward relations, as they will be generated on relations init
        for name, field in model._meta.fields_map.items():
            if isinstance(field, BackwardFKRelation):
                continue

            if isinstance(field, ManyToManyFieldInstance) and field._generated:
                continue

            fields[name] = field

        return cls(
            app=app_label,
            name=model.__name__,
            table=model._meta.table,
            abstract=model._meta.abstract,
            description=model._meta.table_description,
            options=model._meta.options,
            pk_field_name=model._meta.pk_attr,
            bases=model.__bases__,
            fields=fields,
        )


def get_related_models(model: Type[Model]) -> List[Type[Model]]:
    related_models = [
        subclass for subclass in model.__subclasses__() if issubclass(subclass, Model)
    ]

    for field_name in model._meta.fetch_fields:
        field = cast(RelationalField, model._meta.fields_map[field_name])
        related_models.append(field.model_class)

    return related_models


def get_related_model_tuples(model: Type[Model]) -> Set[Tuple[str, str]]:
    return {(m._meta.app, m.__name__) for m in get_related_models(model)}


def get_related_models_recursive(model: Type[Model]) -> Set[Tuple[str, str]]:
    seen = set()
    rel_models = get_related_models(model)

    for rel_model in rel_models:
        model_tuple = (rel_model._meta.app, rel_model.__name__)
        if model_tuple in seen:
            continue
        seen.add(model_tuple)
        rel_models += get_related_models(rel_model)

    return seen - {(model._meta.app, model.__name__)}


@dataclass
class State:
    models: Dict[Tuple[str, str], ModelState]
    apps: StateApps

    def _find_related_models(self, app_label: str, model_name: str):
        try:
            model = self.apps.get_model(f"{app_label}.{model_name}")
        except LookupError:
            related_models = set()
        else:
            related_models = get_related_models_recursive(model)

        related_models.add((app_label, model_name))

        return related_models

    def _reload(self, models_to_reload: Set[Tuple[str, str]]):
        for app_label, model_name in models_to_reload:
            self.apps.unregister_model(app_label, model_name)
            model_state = self.models[(app_label, model_name)]
            model = model_state.render(self.apps)
            self.apps.register_model(app_label, model)

        self.apps._init_relations()

    def reload_model(self, app_label: str, model_name: str):
        model_state = self.models.get((app_label, model_name))
        if not model_state:
            raise LookupError(f"Model state {app_label}.{model_name} is unknown")

        related_models = self._find_related_models(app_label, model_name)
        self._reload(related_models)

    def reload_models(self, model_tuples: Iterable[Tuple[str, str]]):
        related_models = set()

        for app_label, model_name in model_tuples:
            model_state = self.models.get((app_label, model_name))
            if not model_state:
                raise LookupError(f"Model state {app_label}.{model_name} is unknown")

            related_models |= self._find_related_models(app_label, model_name)

        self._reload(related_models)

    def clone(self) -> "State":
        models = {key: model.clone() for key, model in self.models.items()}
        return self.__class__(models=models, apps=self.apps.clone())
