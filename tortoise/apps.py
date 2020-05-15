import importlib
import warnings
from copy import deepcopy
from inspect import isclass
from itertools import chain
from typing import Dict, Iterable, List, Tuple, Type, cast

from pypika import Table

from tortoise.connection_repository import ConnectionRepository
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


class TortoiseApplication:
    def __init__(self, label: str, models: List[Type[Model]]):
        self.label = label
        self.models: Dict[str, Type[Model]] = {model.__name__: model for model in models}

    def get_model(self, name: str) -> Type[Model]:
        return self.models[name]


class Apps:
    def __init__(self, config: dict, connections: ConnectionRepository):
        self.config = config
        self.connection_repository = connections
        self.apps: Dict[str, TortoiseApplication] = {}
        if self.config:
            self._load_from_config()

    @staticmethod
    def _discover_models(models_path: str, app_label: str) -> List[Type[Model]]:
        try:
            module = importlib.import_module(models_path)
        except ImportError:
            raise ConfigurationError(f'Module "{models_path}" not found')
        discovered_models = []
        possible_models = getattr(module, "__models__", None)
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
                attr._meta.finalise_pk()
                discovered_models.append(attr)
        if not discovered_models:
            warnings.warn(f'Module "{models_path}" has no models', RuntimeWarning, stacklevel=4)
        return discovered_models

    def init_app(
        self, label: str, module_list: List[str], _init_relations: bool = True
    ) -> TortoiseApplication:
        app_models: List[Type[Model]] = []
        for module in module_list:
            app_models += self._discover_models(module, label)

        self.apps[label] = TortoiseApplication(label, app_models)

        if _init_relations:
            self._init_relations()

        return self.apps[label]

    def _build_initial_querysets(self) -> None:
        for app in self.apps.values():
            for model in app.models.values():
                model._meta.finalise_model()
                model._meta.basetable = Table(model._meta.table)
                model._meta.basequery = model._meta.db.query_class.from_(model._meta.table)
                model._meta.basequery_all_fields = model._meta.basequery.select(
                    *model._meta.db_fields
                )

    def _load_from_config(self) -> None:
        for name, info in self.config.items():
            try:
                self.connection_repository[info.get("default_connection", "default")]
            except KeyError:
                raise ConfigurationError(
                    'Unknown connection "{}" for app "{}"'.format(
                        info.get("default_connection", "default"), name
                    )
                )

            self.init_app(name, info["models"], _init_relations=False)

            for model in self.apps[name].models.values():
                model._meta.default_connection = info.get("default_connection", "default")

        self._init_relations()
        self._build_initial_querysets()

    def _init_fk_relations(self, model: Type[Model]) -> None:
        for field in model._meta.fk_fields:
            fk_object = cast(ForeignKeyFieldInstance, model._meta.fields_map[field])
            reference = fk_object.model_name
            related_app_name, related_model_name = self.split_reference(reference)
            related_model = self.get_model(related_app_name, related_model_name)

            if fk_object.to_field:
                related_field = related_model._meta.fields_map.get(fk_object.to_field, None)
                if related_field:
                    if related_field.unique:
                        key_fk_object = deepcopy(related_field)
                        fk_object.to_field_instance = related_field
                    else:
                        raise ConfigurationError(
                            f'field "{fk_object.to_field}" in model'
                            f' "{related_model_name}" is not unique'
                        )
                else:
                    raise ConfigurationError(
                        f'there is no field named "{fk_object.to_field}"'
                        f' in model "{related_model_name}"'
                    )
            else:
                key_fk_object = deepcopy(related_model._meta.pk)
                fk_object.to_field_instance = related_model._meta.pk

            key_field = f"{field}_id"
            key_fk_object.pk = False
            key_fk_object.unique = False
            key_fk_object.index = fk_object.index
            key_fk_object.default = fk_object.default
            key_fk_object.null = fk_object.null
            key_fk_object.generated = fk_object.generated
            key_fk_object.reference = fk_object
            key_fk_object.description = fk_object.description
            if fk_object.source_field:
                key_fk_object.source_field = fk_object.source_field
            else:
                key_fk_object.source_field = key_field
            model._meta.add_field(key_field, key_fk_object)

            fk_object.model_class = related_model
            fk_object.source_field = key_field
            backward_relation_name = fk_object.related_name
            if backward_relation_name is not False:
                if not backward_relation_name:
                    backward_relation_name = f"{model._meta.table}s"
                if backward_relation_name in related_model._meta.fields:
                    raise ConfigurationError(
                        f'backward relation "{backward_relation_name}" duplicates in'
                        f" model {related_model_name}"
                    )
                fk_relation = BackwardFKRelation(
                    model, f"{field}_id", fk_object.null, fk_object.description,
                )
                fk_relation.to_field_instance = fk_object.to_field_instance
                related_model._meta.add_field(backward_relation_name, fk_relation)

    def _init_o2o_relations(self, model: Type[Model]) -> None:
        for field in model._meta.o2o_fields:
            o2o_object = cast(OneToOneFieldInstance, model._meta.fields_map[field])
            reference = o2o_object.model_name
            related_app_name, related_model_name = self.split_reference(reference)
            related_model = self.get_model(related_app_name, related_model_name)

            if o2o_object.to_field:
                related_field = related_model._meta.fields_map.get(o2o_object.to_field, None)
                if related_field:
                    if related_field.unique:
                        key_o2o_object = deepcopy(related_field)
                        o2o_object.to_field_instance = related_field
                    else:
                        raise ConfigurationError(
                            f'field "{o2o_object.to_field}" in model'
                            f' "{related_model_name}" is not unique'
                        )
                else:
                    raise ConfigurationError(
                        f'there is no field named "{o2o_object.to_field}"'
                        f' in model "{related_model_name}"'
                    )
            else:
                key_o2o_object = deepcopy(related_model._meta.pk)
                o2o_object.to_field_instance = related_model._meta.pk

            key_field = f"{field}_id"
            key_o2o_object.pk = o2o_object.pk
            key_o2o_object.index = o2o_object.index
            key_o2o_object.default = o2o_object.default
            key_o2o_object.null = o2o_object.null
            key_o2o_object.unique = o2o_object.unique
            key_o2o_object.generated = o2o_object.generated
            key_o2o_object.reference = o2o_object
            key_o2o_object.description = o2o_object.description
            if o2o_object.source_field:
                key_o2o_object.source_field = o2o_object.source_field
            else:
                key_o2o_object.source_field = key_field
            model._meta.add_field(key_field, key_o2o_object)

            o2o_object.model_class = related_model
            o2o_object.source_field = key_field
            backward_relation_name = o2o_object.related_name
            if backward_relation_name is not False:
                if not backward_relation_name:
                    backward_relation_name = f"{model._meta.table}"
                if backward_relation_name in related_model._meta.fields:
                    raise ConfigurationError(
                        f'backward relation "{backward_relation_name}" duplicates in'
                        f" model {related_model_name}"
                    )
                o2o_relation = BackwardOneToOneRelation(
                    model, f"{field}_id", null=True, description=o2o_object.description,
                )
                o2o_relation.to_field_instance = o2o_object.to_field_instance
                related_model._meta.add_field(backward_relation_name, o2o_relation)

            if o2o_object.pk:
                model._meta.pk_attr = key_field

    def _init_m2m_relations(self, model: Type[Model], app_name: str, model_name: str):
        for field in list(model._meta.m2m_fields):
            m2m_object = cast(ManyToManyFieldInstance, model._meta.fields_map[field])
            if m2m_object._generated:
                continue

            backward_key = m2m_object.backward_key
            if not backward_key:
                backward_key = f"{model._meta.table}_id"
                if backward_key == m2m_object.forward_key:
                    backward_key = f"{model._meta.table}_rel_id"
                m2m_object.backward_key = backward_key

            reference = m2m_object.model_name
            related_app_name, related_model_name = self.split_reference(reference)
            related_model = self.get_model(related_app_name, related_model_name)

            m2m_object.model_class = related_model

            backward_relation_name = m2m_object.related_name
            if not backward_relation_name:
                backward_relation_name = m2m_object.related_name = f"{model._meta.table}s"
            if backward_relation_name in related_model._meta.fields:
                raise ConfigurationError(
                    f'backward relation "{backward_relation_name}" duplicates in'
                    f" model {related_model_name}"
                )

            if not m2m_object.through:
                related_model_table_name = (
                    related_model._meta.table
                    if related_model._meta.table
                    else related_model.__name__.lower()
                )

                m2m_object.through = f"{model._meta.table}_{related_model_table_name}"

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

    def _init_relations(self) -> None:
        for app_name, app in self.apps.items():
            for model_name, model in app.models.items():
                if model._meta._inited:
                    continue
                model._meta._inited = True
                if not model._meta.table:
                    model._meta.table = model.__name__.lower()
                pk_attr_cached = model._meta.pk_attr

                # TODO: refactor to share logic between FK & O2O
                self._init_fk_relations(model)
                self._init_o2o_relations(model)
                self._init_m2m_relations(model, app_name, model_name)
                # New pk field could be generated when creating key field for relation
                pk_attr_changed = model._meta.pk_attr != pk_attr_cached

                if pk_attr_changed:
                    model._meta.finalise_pk()

    def get_model_reference(self, model: Type[Model]) -> str:
        name = model._meta.table
        for app in self.apps.values():  # pragma: nobranch
            for _name, _model in app.models.items():  # pragma: nobranch
                if model == _model:
                    name = _name
        return f"{model._meta.app}.{name}"

    @staticmethod
    def split_reference(reference: str) -> Tuple[str, str]:
        """
        Test, if reference follow the official naming conventions. Throws a
        ConfigurationError with a hopefully helpful message. If successfull,
        returns the app and the model name.

        :raises ConfigurationError: If no model reference is invalid.
        """
        items = reference.split(".")
        if len(items) != 2:  # pragma: nocoverage
            raise ConfigurationError(
                (
                    "'%s' is not a valid model reference Bad Reference."
                    " Should be something like <appname>.<modelname>."
                )
                % reference
            )

        return (items[0], items[1])

    def get_model(self, related_app_name: str, related_model_name: str) -> Type[Model]:
        """
        Test, if app and model really exist. Throws a ConfigurationError with a hopefully
        helpful message. If successful, returns the requested model.

        :raises ConfigurationError: If no such app or model exists.
        """
        try:
            return self.apps[related_app_name].get_model(related_model_name)
        except KeyError:
            if related_app_name not in self.apps:
                raise ConfigurationError(f"No app with name '{related_app_name}' registered.")
            raise ConfigurationError(
                f"No model with name '{related_model_name}' registered in"
                f" app '{related_app_name}'."
            )

    def get_models_iterable(self) -> Iterable[Type[Model]]:
        model_list_generator = (
            model_list for model_list in (app.models.values() for app in self.apps.values())
        )
        return chain.from_iterable(model_list_generator)

    def __getitem__(self, key: str) -> TortoiseApplication:
        return self.apps[key]

    def __setitem__(self, key: str, value: TortoiseApplication):
        self.apps[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.apps

    def __iter__(self):
        return self.apps.__iter__()
