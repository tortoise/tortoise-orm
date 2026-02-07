from __future__ import annotations

import inspect
from collections.abc import Iterable
from copy import copy
from dataclasses import dataclass
from typing import Any, cast

from tortoise.fields.base import Field
from tortoise.fields.relational import BackwardFKRelation, ManyToManyFieldInstance, RelationalField
from tortoise.migrations.schema_generator.state_apps import StateApps
from tortoise.models import Model


@dataclass
class BaseEntityState:
    @classmethod
    def from_dict(cls, env) -> BaseEntityState:
        return cls(**{k: v for k, v in env.items() if k in inspect.signature(cls).parameters})


@dataclass
class ModelState(BaseEntityState):
    name: str
    app: str
    table: str
    abstract: bool
    description: str
    options: dict[str, Any]
    bases: tuple[type, ...]
    pk_field_name: str
    fields: dict[str, Field]

    def clone(self) -> ModelState:
        return self.__class__(
            name=self.name,
            app=self.app,
            table=self.table,
            abstract=self.abstract,
            description=self.description,
            options=dict(self.options),
            bases=self.bases,
            pk_field_name=self.pk_field_name,
            fields={name: copy(field) for name, field in self.fields.items()},
        )

    def render(self, apps: StateApps, *, deepcopy_fields: bool = True) -> type[Model]:
        meta_class = type("Meta", (), self.options)

        if deepcopy_fields:
            attrs: dict[str, Any] = {name: copy(field) for name, field in self.fields.items()}
        else:
            attrs = dict(self.fields)
        attrs["Meta"] = meta_class
        attrs["_no_comments"] = True

        model = type(self.name, self.bases, attrs)
        return cast(type[Model], model)

    @classmethod
    def make_from_model(cls, app_label: str, model: type[Model]) -> ModelState:
        fields: dict[str, Field] = {}

        for name, field in model._meta.fields_map.items():
            if isinstance(field, BackwardFKRelation):
                continue

            if isinstance(field, ManyToManyFieldInstance) and field._generated:
                continue
            if getattr(field, "reference", None) is not None:
                continue

            fields[name] = copy(field)

        options: dict[str, Any] = {}
        if model._meta.abstract:
            options["abstract"] = model._meta.abstract
        if model._meta.db_table:
            options["table"] = model._meta.db_table
        if model._meta.schema:
            options["schema"] = model._meta.schema
        if model._meta.app:
            options["app"] = model._meta.app
        if model._meta.unique_together:
            options["unique_together"] = model._meta.unique_together
        if model._meta.indexes:
            options["indexes"] = model._meta.indexes
        if model._meta.pk_attr:
            options["pk_attr"] = model._meta.pk_attr
        if model._meta.table_description:
            options["table_description"] = model._meta.table_description

        return cls(
            app=app_label,
            name=model.__name__,
            table=model._meta.db_table,
            abstract=model._meta.abstract,
            description=model._meta.table_description,
            options=options,
            pk_field_name=model._meta.pk_attr,
            bases=model.__bases__,
            fields=fields,
        )


def get_related_models(model: type[Model]) -> list[type[Model]]:
    related_models = [
        subclass for subclass in model.__subclasses__() if issubclass(subclass, Model)
    ]

    for field_name in model._meta.fetch_fields:
        field = cast(RelationalField, model._meta.fields_map[field_name])
        # related_model may be None if the target model hasn't been registered yet
        # (e.g. during migration state-building when CreateModel operations are
        # processed in alphabetical order).
        if field.related_model is not None:
            related_models.append(field.related_model)

    return related_models


def _require_app_label(model: type[Model]) -> str:
    app_label = model._meta.app
    if app_label is None:
        raise ValueError(f"Model {model} is not registered in any app")
    return app_label


def get_related_model_tuples(model: type[Model]) -> set[tuple[str, str]]:
    return {(_require_app_label(m), m.__name__) for m in get_related_models(model)}


def get_related_models_recursive(model: type[Model]) -> set[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    rel_models = get_related_models(model)

    for rel_model in rel_models:
        model_tuple = (_require_app_label(rel_model), rel_model.__name__)
        if model_tuple in seen:
            continue
        seen.add(model_tuple)
        rel_models += get_related_models(rel_model)

    return seen - {(_require_app_label(model), model.__name__)}


@dataclass
class State:
    models: dict[tuple[str, str], ModelState]
    apps: StateApps

    def _find_related_models(self, app_label: str, model_name: str) -> set[tuple[str, str]]:
        try:
            model = self.apps.get_model(f"{app_label}.{model_name}")
        except KeyError:
            related_models: set[tuple[str, str]] = set()
        else:
            related_models = get_related_models_recursive(model)

        related_models.add((app_label, model_name))

        return related_models

    def _reload(self, models_to_reload: set[tuple[str, str]]) -> None:
        for app_label, model_name in models_to_reload:
            self.apps.unregister_model(app_label, model_name)
            model_state = self.models[(app_label, model_name)]
            model = model_state.render(self.apps)
            self.apps.register_model(app_label, model)

        self.apps._init_relations()
        self.apps._build_initial_querysets()

    def reload_model(self, app_label: str, model_name: str) -> None:
        model_state = self.models.get((app_label, model_name))
        if not model_state:
            raise LookupError(f"Model state {app_label}.{model_name} is unknown")

        related_models = self._find_related_models(app_label, model_name)
        self._reload(related_models)

    def reload_models(self, model_tuples: Iterable[tuple[str, str]]) -> None:
        related_models: set[tuple[str, str]] = set()

        for app_label, model_name in model_tuples:
            model_state = self.models.get((app_label, model_name))
            if not model_state:
                continue

            related_models |= self._find_related_models(app_label, model_name)

        self._reload(related_models)

    def validate_relations_initialized(self) -> None:
        """Verify that all registered models have had their relations fully initialized.

        Raises ``RuntimeError`` if any model still has ``_inited = False``, which
        indicates a relational field whose target was never resolved.  This acts as
        a safety-net for the deferred-init logic in ``StateApps._init_relations``.
        """
        uninited: list[str] = []
        for app in self.apps.apps.values():
            for model in app.values():
                if not model._meta._inited:
                    uninited.append(f"{model._meta.app}.{model.__name__}")
        if uninited:
            raise RuntimeError(
                "The following models still have uninitialized relations after "
                f"applying all operations: {', '.join(sorted(uninited))}. "
                "This usually means a relational field references a model that "
                "was never created in this migration sequence."
            )

    def clone(self) -> State:
        models = {key: model.clone() for key, model in self.models.items()}
        return self.__class__(models=models, apps=self.apps.clone(model_states=models))
