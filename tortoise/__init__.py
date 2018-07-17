from tortoise import fields
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.exceptions import ConfigurationError
from tortoise.models import get_backward_fk_filters, get_m2m_filters


class Tortoise:
    apps = {}  # type: dict
    _inited = False
    _db_routing = None
    _global_connection = None

    @classmethod
    def register_model(cls, app, name, model):
        if app not in cls.apps:
            cls.apps[app] = {}
        if name in cls.apps[app]:
            raise ConfigurationError('{} duplicates in {}'.format(name, app))
        cls.apps[app][name] = model

    @classmethod
    def _set_connection_routing(cls, db_routing):
        if set(db_routing.keys()) != set(cls.apps.keys()):
            raise ConfigurationError('No db instanced for apps: {}'.format(
                ", ".join(set(db_routing.keys()) ^ set(cls.apps.keys()))))
        for app, client in db_routing.items():
            for model in cls.apps[app].values():
                model._meta.db = client

    @classmethod
    def _set_global_connection(cls, db_client):
        for app in cls.apps.values():
            for model in app.values():
                model._meta.db = db_client

    @classmethod
    def _client_routing(cls, global_client=None, db_routing=None):
        if global_client and db_routing:
            raise ConfigurationError('You must pass either global_client or db_routing')
        if global_client:
            if not isinstance(global_client, BaseDBAsyncClient):
                raise ConfigurationError('global_client must inherit from BaseDBAsyncClient')
            cls._set_global_connection(global_client)
        elif db_routing:
            if not all(isinstance(c, BaseDBAsyncClient) for c in db_routing.values()):
                raise ConfigurationError('All app values must inherit from BaseDBAsyncClient')
            cls._set_connection_routing(db_routing)
        else:
            raise ConfigurationError('You must pass either global_client or db_routing')

    @classmethod
    def _init_relations(cls):
        cls._inited = True
        for app_name, app in cls.apps.items():
            for model_name, model in app.items():
                if not model._meta.table:
                    model._meta.table = model.__name__.lower()

                for field in model._meta.fk_fields:
                    field_object = model._meta.fields_map[field]
                    reference = field_object.model_name
                    related_app_name, related_model_name = reference.split('.')
                    related_model = cls.apps[related_app_name][related_model_name]
                    field_object.type = related_model
                    backward_relation_name = field_object.related_name
                    if not backward_relation_name:
                        backward_relation_name = '{}s'.format(model._meta.table)
                    if backward_relation_name in related_model._meta.fields:
                        raise ConfigurationError(
                            'backward relation "{}" duplicates in model {}'.format(
                                backward_relation_name, related_model_name))
                    fk_relation = fields.BackwardFKRelation(model, '{}_id'.format(field))
                    setattr(related_model, backward_relation_name, fk_relation)
                    related_model._meta.filters.update(
                        get_backward_fk_filters(backward_relation_name, fk_relation)
                    )

                    related_model._meta.backward_fk_fields.add(backward_relation_name)
                    related_model._meta.fetch_fields.add(backward_relation_name)
                    related_model._meta.fields_map[backward_relation_name] = fk_relation
                    related_model._meta.fields.add(backward_relation_name)

                for field in model._meta.m2m_fields:
                    field_object = model._meta.fields_map[field]
                    if field_object._generated:
                        continue

                    backward_key = field_object.backward_key
                    if not backward_key:
                        backward_key = '{}_id'.format(model._meta.table)
                        field_object.backward_key = backward_key

                    reference = field_object.model_name
                    related_app_name, related_model_name = reference.split('.')
                    related_model = cls.apps[related_app_name][related_model_name]

                    field_object.type = related_model

                    backward_relation_name = field_object.related_name
                    if not backward_relation_name:
                        backward_relation_name = '{}s'.format(model._meta.table)
                    if backward_relation_name in related_model._meta.fields:
                        raise ConfigurationError(
                            'backward relation "{}" duplicates in model {}'.format(
                                backward_relation_name, related_model_name))

                    if not field_object.through:
                        related_model_table_name = (
                            related_model._meta.table
                            if related_model._meta.table else related_model.__name__.lower()
                        )

                        field_object.through = '{}_{}'.format(
                            model._meta.table,
                            related_model_table_name,
                        )

                    m2m_relation = fields.ManyToManyField(
                        '{}.{}'.format(app_name, model_name),
                        field_object.through,
                        forward_key=field_object.backward_key,
                        backward_key=field_object.forward_key,
                        related_name=field,
                        type=model
                    )
                    m2m_relation._generated = True
                    setattr(
                        related_model,
                        backward_relation_name,
                        m2m_relation,
                    )
                    model._meta.filters.update(get_m2m_filters(field, field_object))
                    related_model._meta.filters.update(
                        get_m2m_filters(backward_relation_name, m2m_relation)
                    )
                    related_model._meta.m2m_fields.add(backward_relation_name)
                    related_model._meta.fetch_fields.add(backward_relation_name)
                    related_model._meta.fields_map[backward_relation_name] = m2m_relation
                    related_model._meta.fields.add(backward_relation_name)

    @classmethod
    def init(cls, global_client=None, db_routing=None):
        if cls._inited:
            raise ConfigurationError('Already initialised')
        cls._client_routing(global_client=global_client, db_routing=db_routing)
        cls._init_relations()


__version__ = "0.9.4"
