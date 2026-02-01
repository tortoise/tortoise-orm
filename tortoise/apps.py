from __future__ import annotations

import importlib
import warnings
from collections.abc import Callable, Iterable, Iterator
from copy import deepcopy
from inspect import isclass
from itertools import chain
from types import ModuleType
from typing import Any, cast

from pypika_tortoise import Query, Table

from tortoise.connection import ConnectionHandler
from tortoise.exceptions import ConfigurationError
from tortoise.fields.relational import (
    BackwardFKRelation,
    BackwardOneToOneRelation,
    ForeignKeyFieldInstance,
    ManyToManyFieldInstance,
    OneToOneFieldInstance,
)
from tortoise.filters import get_m2m_filters
from tortoise.models import Model


class Apps:
    def __init__(
        self,
        config: dict[str, dict[str, Any]] | None,
        connections: ConnectionHandler,
        table_name_generator: Callable[[type[Model]], str] | None = None,
        *,
        validate_connections: bool = True,
    ) -> None:
        self.apps: dict[str, dict[str, type[Model]]] = {}
        self._config = config or {}
        self._connections = connections
        self._table_name_generator = table_name_generator
        self._validate_connections = validate_connections
        if self._config:
            self._load_from_config()

    @staticmethod
    def _discover_models(models_path: ModuleType | str, app_label: str) -> list[type[Model]]:
        if isinstance(models_path, ModuleType):
            module = models_path
        else:
            try:
                module = importlib.import_module(models_path)
            except ImportError:
                raise ConfigurationError(f'Module "{models_path}" not found')
        discovered_models: list[type[Model]] = []
        if possible_models := getattr(module, "__models__", None):
            try:
                possible_models = [*possible_models]
            except TypeError:
                possible_models = None
        if not possible_models:
            possible_models = [getattr(module, attr_name) for attr_name in dir(module)]
        for attr in possible_models:
            if isclass(attr) and issubclass(attr, Model) and not attr._meta.abstract:
                if attr._meta.app and attr._meta.app != app_label:
                    continue
                attr._meta.app = app_label
                discovered_models.append(attr)
        if not discovered_models:
            warnings.warn(f'Module "{models_path}" has no models', RuntimeWarning, stacklevel=4)
        return discovered_models

    def init_app(
        self,
        label: str,
        module_list: Iterable[ModuleType | str],
        _init_relations: bool = True,
    ) -> dict[str, type[Model]]:
        app_models: list[type[Model]] = []
        for module in module_list:
            app_models += self._discover_models(module, label)

        self.apps[label] = {model.__name__: model for model in app_models}

        if _init_relations:
            self._init_relations()

        return self.apps[label]

    def _load_from_config(self) -> None:
        for name, info in self._config.items():
            default_connection = info.get("default_connection", "default")
            if self._validate_connections:
                try:
                    self._connections.get(default_connection)
                except KeyError:
                    raise ConfigurationError(
                        f'Unknown connection "{default_connection}" for app "{name}"'
                    )
            else:
                if default_connection not in self._connections.db_config:
                    raise ConfigurationError(
                        f'Unknown connection "{default_connection}" for app "{name}"'
                    )

            self.init_app(name, info["models"], _init_relations=False)

            for model in self.apps[name].values():
                model._meta.default_connection = default_connection

        self._init_relations()
        if self._validate_connections:
            self._build_initial_querysets()

    def _build_initial_querysets(self) -> None:
        for app in self.apps.values():
            for model in app.values():
                model._meta.finalise_model()
                model._meta.basetable = Table(name=model._meta.db_table, schema=model._meta.schema)
                basequery = model._meta.db.query_class.from_(model._meta.basetable)
                model._meta.basequery = cast(Query, basequery)
                model._meta.basequery_all_fields = cast(
                    Query, basequery.select(*model._meta.db_fields)
                )

    def _init_relations(self) -> None:
        def get_related_model(related_app_name: str, related_model_name: str) -> type[Model]:
            """
            Test, if app and model really exist. Throws a ConfigurationError with a hopefully
            helpful message. If successful, returns the requested model.

            :raises ConfigurationError: If no such app exists.
            """
            try:
                return self.apps[related_app_name][related_model_name]
            except KeyError:
                if related_app_name not in self.apps:
                    raise ConfigurationError(
                        f"No app with name '{related_app_name}' registered."
                        f" Please check your model names in ForeignKeyFields"
                        f" and configurations."
                    )
                raise ConfigurationError(
                    f"No model with name '{related_model_name}' registered in"
                    f" app '{related_app_name}'."
                )

        def split_reference(reference: str) -> tuple[str, str]:
            """
            Validate, if reference follow the official naming conventions. Throws a
            ConfigurationError with a hopefully helpful message. If successful,
            returns the app and the model name.

            :raises ConfigurationError: If reference is invalid.
            """
            if len(items := reference.split(".")) != 2:  # pragma: nocoverage
                raise ConfigurationError(
                    f"'{reference}' is not a valid model reference Bad Reference."
                    " Should be something like '<appname>.<modelname>'."
                )
            return items[0], items[1]

        def init_fk_o2o_field(model: type[Model], field: str, is_o2o: bool = False) -> None:
            fk_object = cast(
                "OneToOneFieldInstance | ForeignKeyFieldInstance", model._meta.fields_map[field]
            )
            reference = fk_object.model_name
            if not isinstance(reference, str):
                related_model: type[Model] = reference
                related_model_name = related_model.__name__
            else:
                related_app_name, related_model_name = split_reference(reference)
                related_model = get_related_model(related_app_name, related_model_name)

            if to_field := fk_object.to_field:
                related_field = related_model._meta.fields_map.get(to_field)
                if not related_field:
                    raise ConfigurationError(
                        f'there is no field named "{to_field}" in model "{related_model_name}"'
                    )
                if not related_field.unique:
                    raise ConfigurationError(
                        f'field "{to_field}" in model "{related_model_name}" is not unique'
                    )
            else:
                fk_object.to_field = related_model._meta.pk_attr
                related_field = related_model._meta.pk
            key_fk_object = deepcopy(related_field)
            fk_object.to_field_instance = related_field
            fk_object.field_type = fk_object.to_field_instance.field_type

            key_field = f"{field}_id"
            key_fk_object.reference = fk_object
            key_fk_object.source_field = fk_object.source_field or key_field
            for attr in ("index", "default", "null", "generated", "description"):
                setattr(key_fk_object, attr, getattr(fk_object, attr))
            if is_o2o:
                key_fk_object.pk = fk_object.pk
                key_fk_object.unique = fk_object.unique
            else:
                key_fk_object.pk = False
                key_fk_object.unique = False
            model._meta.add_field(key_field, key_fk_object)
            fk_object.related_model = related_model
            fk_object.source_field = key_field
            if (backward_relation_name := fk_object.related_name) is not False:
                if not backward_relation_name:
                    backward_relation_name = f"{model._meta.db_table}s"
                if backward_relation_name in related_model._meta.fields:
                    raise ConfigurationError(
                        f'backward relation "{backward_relation_name}" duplicates in'
                        f" model {related_model_name}"
                    )

                fk_relation = (
                    BackwardOneToOneRelation(
                        model,
                        key_field,
                        key_fk_object.source_field,
                        null=True,
                        description=fk_object.description,
                    )
                    if is_o2o
                    else BackwardFKRelation(
                        model,
                        key_field,
                        key_fk_object.source_field,
                        null=fk_object.null,
                        description=fk_object.description,
                    )
                )
                fk_relation.to_field_instance = fk_object.to_field_instance
                related_model._meta.add_field(backward_relation_name, fk_relation)
            if is_o2o and fk_object.pk:
                model._meta.pk_attr = key_field

        for app_name, app in self.apps.items():
            for model_name, model in app.items():
                if model._meta._inited:
                    continue
                model._meta._inited = True
                if not model._meta.db_table:
                    model._meta.db_table = (
                        self._table_name_generator(model)
                        if self._table_name_generator
                        else (model.__name__.lower())
                    )

                for field in sorted(model._meta.fk_fields):
                    init_fk_o2o_field(model, field)

                for field in model._meta.o2o_fields:
                    init_fk_o2o_field(model, field, is_o2o=True)

                for field in list(model._meta.m2m_fields):
                    m2m_object = cast(ManyToManyFieldInstance, model._meta.fields_map[field])
                    if m2m_object._generated:
                        continue
                    if not (backward_key := m2m_object.backward_key):
                        backward_key = f"{model._meta.db_table}_id"
                        if backward_key == m2m_object.forward_key:
                            backward_key = f"{model._meta.db_table}_rel_id"
                        m2m_object.backward_key = backward_key

                    reference = m2m_object.model_name
                    if not isinstance(reference, str):
                        related_model = reference
                        related_model_name = related_model.__name__
                    else:
                        related_app_name, related_model_name = split_reference(reference)
                        related_model = get_related_model(related_app_name, related_model_name)

                    m2m_object.related_model = related_model

                    if not (backward_relation_name := m2m_object.related_name):
                        backward_relation_name = m2m_object.related_name = (
                            f"{model._meta.db_table}s"
                        )
                    if backward_relation_name in related_model._meta.fields:
                        raise ConfigurationError(
                            f'backward relation "{backward_relation_name}" duplicates in'
                            f" model {related_model_name}"
                        )

                    if not m2m_object.through:
                        related_model_table_name = (
                            related_model._meta.db_table or related_model.__name__.lower()
                        )
                        m2m_object.through = f"{model._meta.db_table}_{related_model_table_name}"

                    m2m_relation = ManyToManyFieldInstance(
                        f"{app_name}.{model_name}",
                        m2m_object.through,
                        forward_key=m2m_object.backward_key,
                        backward_key=m2m_object.forward_key,
                        related_name=field,
                        field_type=model,
                        description=m2m_object.description,
                    )
                    m2m_relation._generated = True
                    model._meta.filters.update(get_m2m_filters(field, m2m_object))
                    related_model._meta.add_field(backward_relation_name, m2m_relation)

    def get_model_reference(self, model: type[Model]) -> str:
        return model._meta.full_name

    def get_model(self, app_label: str, model_name: str) -> type[Model]:
        try:
            return self.apps[app_label][model_name]
        except KeyError:
            if app_label not in self.apps:
                raise ConfigurationError(f"No app with name '{app_label}' registered.")
            raise ConfigurationError(
                f"No model with name '{model_name}' registered in app '{app_label}'."
            )

    def get_models_iterable(self) -> Iterable[type[Model]]:
        model_list_generator = (
            model_list for model_list in (app.values() for app in self.apps.values())
        )
        return chain.from_iterable(model_list_generator)

    def clear(self) -> None:
        self.apps.clear()

    def __contains__(self, key: str) -> bool:
        return key in self.apps

    def __iter__(self) -> Iterator[str]:
        return self.apps.__iter__()

    def values(self) -> Iterable[dict[str, type[Model]]]:
        return self.apps.values()

    def items(self) -> Iterable[tuple[str, dict[str, type[Model]]]]:
        return self.apps.items()

    def keys(self) -> Iterable[str]:
        return self.apps.keys()

    def __getitem__(self, key: str) -> dict[str, type[Model]]:
        return self.apps[key]

    def __setitem__(self, key: str, value: dict[str, type[Model]]) -> None:
        self.apps[key] = value
