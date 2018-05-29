from tortoise import fields
from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.exceptions import MultiplyObjectsReturned
from tortoise.fields import ManyToManyRelationManager
from tortoise.models import get_backward_fk_filters, get_m2m_filters
from tortoise.queryset import QuerySet


class Tortoise:
    apps = {}
    _inited = False
    _db_routing = None
    _global_connection = None

    @classmethod
    def register_model(cls, app, name, model):
        if app not in cls.apps:
            cls.apps[app] = {}
        assert name not in cls.apps[app], '{} duplicates in {}'.format(name, app)
        cls.apps[app][name] = model

    @classmethod
    def _set_connection_routing(cls, db_routing):
        assert set(db_routing.keys()) == set(cls.apps.keys()), (
            'No db instanced for apps: {}'
            .format(", ".join(set(db_routing.keys()) ^ set(cls.apps.keys())))
        )
        for app, client in db_routing.items():
            for model in cls.apps[app].values():
                model._meta.db = client

    @classmethod
    def _set_global_connection(cls, db_client):
        for app in cls.apps.values():
            for model in app.values():
                model._meta.db = db_client

    @classmethod
    def init(cls, global_client=None, db_routing=None):
        assert bool(global_client) != bool(db_routing), (
            'You must pass either global connection or routing'
        )
        if global_client:
            assert isinstance(global_client, BaseDBAsyncClient)
            cls._set_global_connection(global_client)
        else:
            assert all(isinstance(c, BaseDBAsyncClient) for c in db_routing.values())
            cls._set_connection_routing(db_routing)

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
                    assert backward_relation_name not in related_model._meta.fields, (
                        'backward relation "{}" duplicates in model {}'.format(
                            backward_relation_name,
                            related_model_name
                        )
                    )
                    relation = fields.BackwardFKRelation(model, '{}_id'.format(field))
                    setattr(related_model, backward_relation_name, relation)
                    related_model._meta.filters.update(
                        get_backward_fk_filters(backward_relation_name, relation)
                    )

                    related_model._meta.backward_fk_fields.add(backward_relation_name)
                    related_model._meta.fetch_fields.add(backward_relation_name)
                    related_model._meta.fields_map[backward_relation_name] = relation
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
                    assert backward_relation_name not in related_model._meta.fields, (
                        'backward relation "{}" duplicates in model {}'.format(
                            backward_relation_name,
                            related_model_name
                        )
                    )
                    relation = fields.ManyToManyField(
                        '{}.{}'.format(app_name, model_name),
                        field_object.through,
                        forward_key=field_object.backward_key,
                        backward_key=field_object.forward_key,
                        related_name=field,
                        type=model
                    )
                    relation._generated = True
                    setattr(
                        related_model,
                        backward_relation_name,
                        relation,
                    )
                    model._meta.filters.update(get_m2m_filters(field, field_object))
                    related_model._meta.filters.update(get_m2m_filters(backward_relation_name, relation))
                    related_model._meta.m2m_fields.add(backward_relation_name)
                    related_model._meta.fetch_fields.add(backward_relation_name)
                    related_model._meta.fields_map[backward_relation_name] = relation
                    related_model._meta.fields.add(backward_relation_name)

        cls._inited = True


__version__ = "0.7.10"
