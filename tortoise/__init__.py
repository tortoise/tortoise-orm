import asyncio
import importlib
import json
import logging
import os
import warnings
from copy import deepcopy
from inspect import isclass
from typing import Any, Coroutine, Dict, List, Optional, Tuple, Type, Union, cast

from pypika import Table

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.backends.base.config_generator import expand_db_url, generate_config
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
from tortoise.queryset import QuerySet
from tortoise.transactions import current_transaction_map
from tortoise.utils import generate_schema_for_client

try:
    from contextvars import ContextVar
except ImportError:  # pragma: nocoverage
    from aiocontextvars import ContextVar  # type: ignore

logger = logging.getLogger("tortoise")


class Tortoise:
    apps: Dict[str, Dict[str, Type[Model]]] = {}
    _connections: Dict[str, BaseDBAsyncClient] = {}
    _inited: bool = False

    @classmethod
    def get_connection(cls, connection_name: str) -> BaseDBAsyncClient:
        """
        Returns the connection by name.

        :raises KeyError: If connection name does not exist.
        """
        return cls._connections[connection_name]

    @classmethod
    def describe_model(cls, model: Type[Model], serializable: bool = True) -> dict:
        """
        Describes the given list of models or ALL registered models.

        :param model:
            The Model to describe

        :param serializable:
            ``False`` if you want raw python objects,
            ``True`` for JSON-serialisable data. (Defaults to ``True``)

        :return:
            A dictionary containing the model description.

            The base dict has a fixed set of keys that reference a list of fields
            (or a single field in the case of the primary key):

            .. code-block:: python3

                {
                    "name":                 str     # Qualified model name
                    "app":                  str     # 'App' namespace
                    "table":                str     # DB table name
                    "abstract":             bool    # Is the model Abstract?
                    "description":          str     # Description of table (nullable)
                    "unique_together":      [...]   # List of List containing field names that
                                                    #  are unique together
                    "pk_field":             {...}   # Primary key field
                    "data_fields":          [...]   # Data fields
                    "fk_fields":            [...]   # Foreign Key fields FROM this model
                    "backward_fk_fields":   [...]   # Foreign Key fields TO this model
                    "o2o_fields":           [...]   # OneToOne fields FROM this model
                    "backward_o2o_fields":  [...]   # OneToOne fields TO this model
                    "m2m_fields":           [...]   # Many-to-Many fields
                }

            Each field is specified as follows
            (This assumes ``serializable=True``, which is the default):

            .. code-block:: python3

                {
                    "name":         str     # Field name
                    "field_type":   str     # Field type
                    "db_column":    str     # Name of DB column
                                            #  Optional: Only for pk/data fields
                    "raw_field":    str     # Name of raw field of the Foreign Key
                                            #  Optional: Only for Foreign Keys
                    "db_field_types": dict  # DB Field types for default and DB overrides
                    "python_type":  str     # Python type
                    "generated":    bool    # Is the field generated by the DB?
                    "nullable":     bool    # Is the column nullable?
                    "unique":       bool    # Is the field unique?
                    "indexed":      bool    # Is the field indexed?
                    "default":      ...     # The default value (coerced to int/float/str/bool/null)
                    "description":  str     # Description of the field (nullable)
                }

            When ``serializable=False`` is specified some fields are not coerced to valid
            JSON types. The changes are:

            .. code-block:: python3

                {
                    "field_type":   Field   # The Field class used
                    "python_type":  Type    # The actual Python type
                    "default":      ...     # The default value as native type OR a callable
                }
        """

        def _type_name(typ: Type) -> str:
            if typ.__module__ == "builtins":
                return typ.__name__
            return f"{typ.__module__}.{typ.__name__}"

        def model_name(typ: Type[Model]) -> str:
            name = typ._meta.table
            for app in cls.apps.values():  # pragma: nobranch
                for _name, _model in app.items():  # pragma: nobranch
                    if typ == _model:
                        name = _name
            return f"{typ._meta.app}.{name}"

        def type_name(typ: Any) -> Union[str, List[str]]:
            try:
                if issubclass(typ, Model):
                    return model_name(typ)
            except TypeError:
                pass
            try:
                return _type_name(typ)
            except AttributeError:
                return [_type_name(_typ) for _typ in typ]

        def default_name(default: Any) -> Optional[Union[int, float, str, bool]]:
            if isinstance(default, (int, float, str, bool, type(None))):
                return default
            if callable(default):
                return f"<function {default.__module__}.{default.__name__}>"
            return str(default)

        def describe_field(name: str) -> dict:
            # TODO: db_type
            field = model._meta.fields_map[name]
            field_type = getattr(field, "model_class", field.field_type)
            desc = {
                "name": name,
                "field_type": field.__class__.__name__ if serializable else field.__class__,
                "db_column": field.source_field or name,
                "raw_field": None,
                "db_field_types": field.get_db_field_types(),
                "python_type": type_name(field_type) if serializable else field_type,
                "generated": field.generated,
                "nullable": field.null,
                "unique": field.unique,
                "indexed": field.index or field.unique,
                "default": default_name(field.default) if serializable else field.default,
                "description": field.description,
            }

            # Delete db fields for non-db fields
            if not desc["db_field_types"]:
                del desc["db_field_types"]

            # Foreign Keys have
            if isinstance(field, (ForeignKeyFieldInstance, OneToOneFieldInstance)):
                del desc["db_column"]
                desc["raw_field"] = field.source_field
            else:
                del desc["raw_field"]

            # These fields are entierly "virtual", so no direct DB representation
            if isinstance(
                field, (ManyToManyFieldInstance, BackwardFKRelation, BackwardOneToOneRelation,),
            ):
                del desc["db_column"]

            return desc

        return {
            "name": model_name(model),
            "app": model._meta.app,
            "table": model._meta.table,
            "abstract": model._meta.abstract,
            "description": model._meta.table_description or None,
            "unique_together": model._meta.unique_together or [],
            "pk_field": describe_field(model._meta.pk_attr),
            "data_fields": [
                describe_field(name)
                for name in model._meta.fields_map.keys()
                if name != model._meta.pk_attr
                and name in (model._meta.fields - model._meta.fetch_fields)
            ],
            "fk_fields": [
                describe_field(name)
                for name in model._meta.fields_map.keys()
                if name in model._meta.fk_fields
            ],
            "backward_fk_fields": [
                describe_field(name)
                for name in model._meta.fields_map.keys()
                if name in model._meta.backward_fk_fields
            ],
            "o2o_fields": [
                describe_field(name)
                for name in model._meta.fields_map.keys()
                if name in model._meta.o2o_fields
            ],
            "backward_o2o_fields": [
                describe_field(name)
                for name in model._meta.fields_map.keys()
                if name in model._meta.backward_o2o_fields
            ],
            "m2m_fields": [
                describe_field(name)
                for name in model._meta.fields_map.keys()
                if name in model._meta.m2m_fields
            ],
        }

    @classmethod
    def describe_models(
        cls, models: Optional[List[Type[Model]]] = None, serializable: bool = True
    ) -> Dict[str, dict]:
        """
        Describes the given list of models or ALL registered models.

        :param models:
            List of models to describe, if not provided then describes ALL registered models

        :param serializable:
            ``False`` if you want raw python objects,
            ``True`` for JSON-serializable data. (Defaults to ``True``)

        :return:
            A dictionary containing the model qualifier as key,
            and the same output as ``describe_model(...)`` as value:

            .. code-block:: python3

                {
                    "models.User": {...},
                    "models.Permission": {...}
                }
        """

        if not models:
            models = []
            for app in cls.apps.values():
                for model in app.values():
                    models.append(model)

        return {
            f"{model._meta.app}.{model.__name__}": cls.describe_model(model, serializable)
            for model in models
        }

    @classmethod
    def _init_relations(cls) -> None:
        def get_related_model(related_app_name: str, related_model_name: str) -> Type[Model]:
            """
            Test, if app and model really exist. Throws a ConfigurationError with a hopefully
            helpful message. If successfull, returns the requested model.
            """
            try:
                return cls.apps[related_app_name][related_model_name]
            except KeyError:
                if related_app_name not in cls.apps:
                    raise ConfigurationError(f"No app with name '{related_app_name}' registered.")
                raise ConfigurationError(
                    f"No model with name '{related_model_name}' registered in"
                    f" app '{related_app_name}'."
                )

        def split_reference(reference: str) -> Tuple[str, str]:
            """
            Test, if reference follow the official naming conventions. Throws a
            ConfigurationError with a hopefully helpful message. If successfull,
            returns the app and the model name.
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

        for app_name, app in cls.apps.items():
            for model_name, model in app.items():
                if model._meta._inited:
                    continue
                model._meta._inited = True
                if not model._meta.table:
                    model._meta.table = model.__name__.lower()

                pk_attr_changed = False

                # TODO: refactor to share logic between FK & O2O
                for field in model._meta.fk_fields:
                    fk_object = cast(ForeignKeyFieldInstance, model._meta.fields_map[field])
                    reference = fk_object.model_name
                    related_app_name, related_model_name = split_reference(reference)
                    related_model = get_related_model(related_app_name, related_model_name)

                    if fk_object.to_field:
                        related_field = related_model._meta.fields_map.get(fk_object.to_field, None)
                        if related_field:
                            if related_field.unique:
                                key_fk_object = deepcopy(related_field)
                                fk_object.to_field_instance = related_field
                                reverse_to_field = fk_object.to_field
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
                        reverse_to_field = "pk"

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
                        fk_object.source_field = key_field
                    else:
                        fk_object.source_field = key_field
                        key_fk_object.source_field = key_field
                    model._meta.add_field(key_field, key_fk_object)

                    fk_object.model_class = related_model
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
                            model,
                            f"{field}_id",
                            fk_object.null,
                            fk_object.description,
                            to_field=reverse_to_field,
                        )
                        related_model._meta.add_field(
                            cast(str, backward_relation_name), fk_relation
                        )

                for field in model._meta.o2o_fields:
                    o2o_object = cast(OneToOneFieldInstance, model._meta.fields_map[field])
                    reference = o2o_object.model_name
                    related_app_name, related_model_name = split_reference(reference)
                    related_model = get_related_model(related_app_name, related_model_name)

                    if o2o_object.to_field:
                        related_field = related_model._meta.fields_map.get(
                            o2o_object.to_field, None
                        )
                        if related_field:
                            if related_field.unique:
                                key_o2o_object = deepcopy(related_field)
                                o2o_object.to_field_instance = related_field
                                reverse_to_field = o2o_object.to_field
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
                        reverse_to_field = "pk"

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
                        o2o_object.source_field = key_field
                    else:
                        o2o_object.source_field = key_field
                        key_o2o_object.source_field = key_field
                    model._meta.add_field(key_field, key_o2o_object)

                    o2o_object.model_class = related_model
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
                            model,
                            f"{field}_id",
                            null=True,
                            description=o2o_object.description,
                            to_field=reverse_to_field,
                        )
                        related_model._meta.add_field(
                            cast(str, backward_relation_name), o2o_relation
                        )

                    if o2o_object.pk:
                        pk_attr_changed = True
                        model._meta.pk_attr = key_field

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
                    related_app_name, related_model_name = split_reference(reference)
                    related_model = get_related_model(related_app_name, related_model_name)

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

                if pk_attr_changed:
                    model._meta.finalise_pk()

    @classmethod
    def _discover_client_class(cls, engine: str) -> BaseDBAsyncClient:
        # Let exception bubble up for transparency
        engine_module = importlib.import_module(engine)

        try:
            client_class = engine_module.client_class  # type: ignore
        except AttributeError:
            raise ConfigurationError(f'Backend for engine "{engine}" does not implement db client')
        return client_class

    @classmethod
    def _discover_models(cls, models_path: str, app_label: str) -> List[Type[Model]]:
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

    @classmethod
    async def _init_connections(cls, connections_config: dict, create_db: bool) -> None:
        for name, info in connections_config.items():
            if isinstance(info, str):
                info = expand_db_url(info)
            client_class = cls._discover_client_class(info.get("engine"))
            db_params = info["credentials"].copy()
            db_params.update({"connection_name": name})
            connection = client_class(**db_params)  # type: ignore
            if create_db:
                await connection.db_create()
            await connection.create_connection(with_db=True)
            cls._connections[name] = connection
            current_transaction_map[name] = ContextVar(name, default=connection)

    @classmethod
    def _init_apps(cls, apps_config: dict) -> None:
        for name, info in apps_config.items():
            try:
                cls.get_connection(info.get("default_connection", "default"))
            except KeyError:
                raise ConfigurationError(
                    'Unknown connection "{}" for app "{}"'.format(
                        info.get("default_connection", "default"), name
                    )
                )
            app_models: List[Type[Model]] = []
            for module in info["models"]:
                app_models += cls._discover_models(module, name)

            models_map = {}
            for model in app_models:
                model._meta.default_connection = info.get("default_connection", "default")
                models_map[model.__name__] = model

            cls.apps[name] = models_map

        cls._init_relations()

        cls._build_initial_querysets()

    @classmethod
    def _get_config_from_config_file(cls, config_file: str) -> dict:
        _, extension = os.path.splitext(config_file)
        if extension in (".yml", ".yaml"):
            import yaml  # pylint: disable=C0415

            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
        elif extension == ".json":
            with open(config_file, "r") as f:
                config = json.load(f)
        else:
            raise ConfigurationError(
                f"Unknown config extension {extension}, only .yml and .json are supported"
            )
        return config

    @classmethod
    def _build_initial_querysets(cls) -> None:
        for app in cls.apps.values():
            for model in app.values():
                model._meta.finalise_model()
                model._meta.basetable = Table(model._meta.table)
                model._meta.basequery = model._meta.db.query_class.from_(model._meta.table)
                model._meta.basequery_all_fields = model._meta.basequery.select(
                    *model._meta.db_fields
                )

    @classmethod
    async def init(
        cls,
        config: Optional[dict] = None,
        config_file: Optional[str] = None,
        _create_db: bool = False,
        db_url: Optional[str] = None,
        modules: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """
        Sets up Tortoise-ORM.

        You can configure using only one of ``config``, ``config_file``
        and ``(db_url, modules)``.

        Parameters
        ----------
        config:
            Dict containing config:

            Example
            -------

            .. code-block:: python3

                {
                    'connections': {
                        # Dict format for connection
                        'default': {
                            'engine': 'tortoise.backends.asyncpg',
                            'credentials': {
                                'host': 'localhost',
                                'port': '5432',
                                'user': 'tortoise',
                                'password': 'qwerty123',
                                'database': 'test',
                            }
                        },
                        # Using a DB_URL string
                        'default': 'postgres://postgres:qwerty123@localhost:5432/events'
                    },
                    'apps': {
                        'models': {
                            'models': ['__main__'],
                            # If no default_connection specified, defaults to 'default'
                            'default_connection': 'default',
                        }
                    }
                }

        config_file:
            Path to .json or .yml (if PyYAML installed) file containing config with
            same format as above.
        db_url:
            Use a DB_URL string. See :ref:`db_url`
        modules:
            Dictionary of ``key``: [``list_of_modules``] that defined "apps" and modules that
            should be discovered for models.
        _create_db:
            If ``True`` tries to create database for specified connections,
            could be used for testing purposes.

        Raises
        ------
        ConfigurationError
            For any configuration error
        """
        if cls._inited:
            await cls.close_connections()
            await cls._reset_apps()
        if int(bool(config) + bool(config_file) + bool(db_url)) != 1:
            raise ConfigurationError(
                'You should init either from "config", "config_file" or "db_url"'
            )

        if config_file:
            config = cls._get_config_from_config_file(config_file)

        if db_url:
            if not modules:
                raise ConfigurationError('You must specify "db_url" and "modules" together')
            config = generate_config(db_url, modules)

        try:
            connections_config = config["connections"]  # type: ignore
        except KeyError:
            raise ConfigurationError('Config must define "connections" section')

        try:
            apps_config = config["apps"]  # type: ignore
        except KeyError:
            raise ConfigurationError('Config must define "apps" section')

        logger.info(
            "Tortoise-ORM startup\n    connections: %s\n    apps: %s",
            str(connections_config),
            str(apps_config),
        )

        await cls._init_connections(connections_config, _create_db)
        cls._init_apps(apps_config)

        cls._inited = True

    @classmethod
    async def close_connections(cls) -> None:
        """
        Close all connections cleanly.

        It is required for this to be called on exit,
        else your event loop may never complete
        as it is waiting for the connections to die.
        """
        for connection in cls._connections.values():
            await connection.close()
        cls._connections = {}
        logger.info("Tortoise-ORM shutdown")

    @classmethod
    async def _reset_apps(cls) -> None:
        for app in cls.apps.values():
            for model in app.values():
                model._meta.default_connection = None
        cls.apps.clear()
        current_transaction_map.clear()

    @classmethod
    async def generate_schemas(cls, safe: bool = True) -> None:
        """
        Generate schemas according to models provided to ``.init()`` method.
        Will fail if schemas already exists, so it's not recommended to be used as part
        of application workflow

        Parameters
        ----------
        safe:
            When set to true, creates the table only when it does not already exist.
        """
        if not cls._inited:
            raise ConfigurationError("You have to call .init() first before generating schemas")
        for connection in cls._connections.values():
            await generate_schema_for_client(connection, safe)

    @classmethod
    async def _drop_databases(cls) -> None:
        """
        Tries to drop all databases provided in config passed to ``.init()`` method.
        Normally should be used only for testing purposes.
        """
        if not cls._inited:
            raise ConfigurationError("You have to call .init() first before deleting schemas")
        for connection in cls._connections.values():
            await connection.close()
            await connection.db_delete()
        cls._connections = {}
        await cls._reset_apps()


def run_async(coro: Coroutine) -> None:
    """
    Simple async runner that cleans up DB connections on exit.
    This is meant for simple scripts.

    Usage::

        from tortoise import Tortoise, run_async

        async def do_stuff():
            await Tortoise.init(
                db_url='sqlite://db.sqlite3',
                models={'models': ['app.models']}
            )

            ...

        run_async(do_stuff())
    """
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.run_until_complete(Tortoise.close_connections())


__version__ = "0.15.12"
