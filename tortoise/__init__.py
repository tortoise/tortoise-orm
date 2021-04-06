import asyncio
import importlib
import json
import logging
import os
import warnings
from contextvars import ContextVar
from copy import deepcopy
from inspect import isclass
from types import ModuleType
from typing import Coroutine, Dict, Iterable, List, Optional, Tuple, Type, Union, cast

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
from tortoise.transactions import current_transaction_map
from tortoise.utils import generate_schema_for_client

logger = logging.getLogger("tortoise")


class Tortoise:
    apps: Dict[str, Dict[str, Type["Model"]]] = {}
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
    def describe_model(
        cls, model: Type["Model"], serializable: bool = True
    ) -> dict:  # pragma: nocoverage
        """
        Describes the given list of models or ALL registered models.

        :param model:
            The Model to describe

        :param serializable:
            ``False`` if you want raw python objects,
            ``True`` for JSON-serialisable data. (Defaults to ``True``)

        See :meth:`tortoise.models.Model.describe`

        .. warning::
           This is deprecated, please use :meth:`tortoise.models.Model.describe` instead
        """
        warnings.warn(
            "Tortoise.describe_model(<MODEL>) is deprecated, please use <MODEL>.describe() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return model.describe(serializable=serializable)

    @classmethod
    def describe_models(
        cls, models: Optional[List[Type["Model"]]] = None, serializable: bool = True
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
            f"{model._meta.app}.{model.__name__}": model.describe(serializable) for model in models
        }

    @classmethod
    def _init_relations(cls) -> None:
        def get_related_model(related_app_name: str, related_model_name: str) -> Type["Model"]:
            """
            Test, if app and model really exist. Throws a ConfigurationError with a hopefully
            helpful message. If successfull, returns the requested model.

            :raises ConfigurationError: If no such app exists.
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

        for app_name, app in cls.apps.items():
            for model_name, model in app.items():
                if model._meta._inited:
                    continue
                model._meta._inited = True
                if not model._meta.db_table:
                    model._meta.db_table = model.__name__.lower()

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
                        fk_object.to_field = related_model._meta.pk_attr

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

                    fk_object.related_model = related_model
                    fk_object.source_field = key_field
                    backward_relation_name = fk_object.related_name
                    if backward_relation_name is not False:
                        if not backward_relation_name:
                            backward_relation_name = f"{model._meta.db_table}s"
                        if backward_relation_name in related_model._meta.fields:
                            raise ConfigurationError(
                                f'backward relation "{backward_relation_name}" duplicates in'
                                f" model {related_model_name}"
                            )
                        fk_relation = BackwardFKRelation(
                            model,
                            f"{field}_id",
                            key_fk_object.source_field,
                            fk_object.null,
                            fk_object.description,
                        )
                        fk_relation.to_field_instance = fk_object.to_field_instance
                        related_model._meta.add_field(backward_relation_name, fk_relation)

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
                        o2o_object.to_field = related_model._meta.pk_attr

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

                    o2o_object.related_model = related_model
                    o2o_object.source_field = key_field
                    backward_relation_name = o2o_object.related_name
                    if backward_relation_name is not False:
                        if not backward_relation_name:
                            backward_relation_name = f"{model._meta.db_table}"
                        if backward_relation_name in related_model._meta.fields:
                            raise ConfigurationError(
                                f'backward relation "{backward_relation_name}" duplicates in'
                                f" model {related_model_name}"
                            )
                        o2o_relation = BackwardOneToOneRelation(
                            model,
                            f"{field}_id",
                            key_o2o_object.source_field,
                            null=True,
                            description=o2o_object.description,
                        )
                        o2o_relation.to_field_instance = o2o_object.to_field_instance
                        related_model._meta.add_field(backward_relation_name, o2o_relation)

                    if o2o_object.pk:
                        model._meta.pk_attr = key_field

                for field in list(model._meta.m2m_fields):
                    m2m_object = cast(ManyToManyFieldInstance, model._meta.fields_map[field])
                    if m2m_object._generated:
                        continue

                    backward_key = m2m_object.backward_key
                    if not backward_key:
                        backward_key = f"{model._meta.db_table}_id"
                        if backward_key == m2m_object.forward_key:
                            backward_key = f"{model._meta.db_table}_rel_id"
                        m2m_object.backward_key = backward_key

                    reference = m2m_object.model_name
                    related_app_name, related_model_name = split_reference(reference)
                    related_model = get_related_model(related_app_name, related_model_name)

                    m2m_object.related_model = related_model

                    backward_relation_name = m2m_object.related_name
                    if not backward_relation_name:
                        backward_relation_name = (
                            m2m_object.related_name
                        ) = f"{model._meta.db_table}s"
                    if backward_relation_name in related_model._meta.fields:
                        raise ConfigurationError(
                            f'backward relation "{backward_relation_name}" duplicates in'
                            f" model {related_model_name}"
                        )

                    if not m2m_object.through:
                        related_model_table_name = (
                            related_model._meta.db_table
                            if related_model._meta.db_table
                            else related_model.__name__.lower()
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

    @classmethod
    def _discover_client_class(cls, engine: str) -> Type[BaseDBAsyncClient]:
        # Let exception bubble up for transparency
        engine_module = importlib.import_module(engine)

        try:
            client_class = engine_module.client_class  # type: ignore
        except AttributeError:
            raise ConfigurationError(f'Backend for engine "{engine}" does not implement db client')
        return client_class

    @classmethod
    def _discover_models(
        cls, models_path: Union[ModuleType, str], app_label: str
    ) -> List[Type["Model"]]:
        if isinstance(models_path, ModuleType):
            module = models_path
        else:
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
            connection = client_class(**db_params)
            if create_db:
                await connection.db_create()
            await connection.create_connection(with_db=True)
            cls._connections[name] = connection
            current_transaction_map[name] = ContextVar(name, default=connection)

    @classmethod
    def init_models(
        cls,
        models_paths: Iterable[Union[ModuleType, str]],
        app_label: str,
        _init_relations: bool = True,
    ) -> None:
        """
        Early initialisation of Tortoise ORM Models.

        Initialise the relationships between Models.
        This does not initialise any database connection.

        :param models_paths: Models paths to initialise
        :param app_label: The app label, e.g. 'models'
        :param _init_relations: Whether to init relations or not

        :raises ConfigurationError: If models are invalid.
        """
        app_models: List[Type[Model]] = []
        for models_path in models_paths:
            app_models += cls._discover_models(models_path, app_label)

        cls.apps[app_label] = {model.__name__: model for model in app_models}

        if _init_relations:
            cls._init_relations()

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

            cls.init_models(info["models"], name, _init_relations=False)

            for model in cls.apps[name].values():
                model._meta.default_connection = info.get("default_connection", "default")

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
                model._meta.basetable = Table(model._meta.db_table)
                model._meta.basequery = model._meta.db.query_class.from_(model._meta.db_table)
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
        modules: Optional[Dict[str, Iterable[Union[str, ModuleType]]]] = None,
        use_tz: bool = False,
        timezone: str = "UTC",
        routers: Optional[List[Union[str, Type]]] = None,
    ) -> None:
        """
        Sets up Tortoise-ORM.

        You can configure using only one of ``config``, ``config_file``
        and ``(db_url, modules)``.

        :param config:
            Dict containing config:

            .. admonition:: Example

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
                            'default': 'postgres://postgres:qwerty123@localhost:5432/test'
                        },
                        'apps': {
                            'my_app': {
                                'models': ['__main__'],
                                # If no default_connection specified, defaults to 'default'
                                'default_connection': 'default',
                            }
                        },
                        'routers': ['path.router1', 'path.router2'],
                        'use_tz': False,
                        'timezone': 'UTC'
                    }

        :param config_file:
            Path to .json or .yml (if PyYAML installed) file containing config with
            same format as above.
        :param db_url:
            Use a DB_URL string. See :ref:`db_url`
        :param modules:
            Dictionary of ``key``: [``list_of_modules``] that defined "apps" and modules that
            should be discovered for models.
        :param _create_db:
            If ``True`` tries to create database for specified connections,
            could be used for testing purposes.
        :param use_tz:
            A boolean that specifies if datetime will be timezone-aware by default or not.
        :param timezone:
            Timezone to use, default is UTC.
        :param routers:
            A list of db routers str path or module.

        :raises ConfigurationError: For any configuration error
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

        use_tz = config.get("use_tz", use_tz)  # type: ignore
        timezone = config.get("timezone", timezone)  # type: ignore
        routers = config.get("routers", routers)  # type: ignore

        # Mask passwords in logs output
        passwords = []
        for name, info in connections_config.items():
            if isinstance(info, str):
                info = expand_db_url(info)
            password = info.get("credentials", {}).get("password")
            if password:
                passwords.append(password)

        str_connection_config = str(connections_config)
        for password in passwords:
            str_connection_config = str_connection_config.replace(
                password,
                # Show one third of the password at beginning (may be better for debugging purposes)
                f"{password[0:len(password) // 3]}***",
            )

        logger.debug(
            "Tortoise-ORM startup\n    connections: %s\n    apps: %s",
            str_connection_config,
            str(apps_config),
        )

        cls._init_timezone(use_tz, timezone)
        await cls._init_connections(connections_config, _create_db)
        cls._init_apps(apps_config)
        cls._init_routers(routers)

        cls._inited = True

    @classmethod
    def _init_routers(cls, routers: Optional[List[Union[str, type]]] = None):
        from tortoise.router import router

        routers = routers or []
        router_cls = []
        for r in routers:
            if isinstance(r, str):
                try:
                    module_name, class_name = r.rsplit(".", 2)
                    router_cls.append(getattr(importlib.import_module(module_name), class_name))
                except Exception:
                    raise ConfigurationError(f"Can't import router from `{r}`")
            elif isinstance(r, type):
                router_cls.append(r)
            else:
                raise ConfigurationError("Router must be either str or type")
        router.init_routers(router_cls)

    @classmethod
    async def close_connections(cls) -> None:
        """
        Close all connections cleanly.

        It is required for this to be called on exit,
        else your event loop may never complete
        as it is waiting for the connections to die.
        """
        tasks = []
        for connection in cls._connections.values():
            tasks.append(connection.close())
        await asyncio.gather(*tasks)
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

        :param safe: When set to true, creates the table only when it does not already exist.

        :raises ConfigurationError: When ``.init()`` has not been called.
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

        :raises ConfigurationError: When ``.init()`` has not been called.
        """
        if not cls._inited:
            raise ConfigurationError("You have to call .init() first before deleting schemas")
        for connection in cls._connections.values():
            await connection.close()
            await connection.db_delete()
        cls._connections = {}
        await cls._reset_apps()

    @classmethod
    def _init_timezone(cls, use_tz: bool, timezone: str) -> None:
        os.environ["USE_TZ"] = str(use_tz)
        os.environ["TIMEZONE"] = timezone


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


__version__ = "0.17.2"
