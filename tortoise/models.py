import operator
from copy import deepcopy
from typing import Awaitable, Dict, Hashable, Optional, Set, Tuple, Type, TypeVar  # noqa

from pypika import Table, functions
from pypika.enums import SqlTypes

from tortoise import fields
from tortoise.backends.base.client import BaseDBAsyncClient  # noqa
from tortoise.exceptions import ConfigurationError, OperationalError
from tortoise.fields import ManyToManyRelationManager, RelationQueryContainer
from tortoise.queryset import QuerySet
from tortoise.transactions import current_transaction_map

MODEL_TYPE = TypeVar('MODEL_TYPE', bound='Model')


def is_in(field, value):
    return field.isin(value)


def not_in(field, value):
    return field.notin(value) | field.isnull()


def not_equal(field, value):
    return field.ne(value) | field.isnull()


def is_null(field, value):
    if value:
        return field.isnull()
    else:
        return field.notnull()


def not_null(field, value):
    if value:
        return field.notnull()
    else:
        return field.isnull()


def contains(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like('%{}%'.format(value))


def starts_with(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like('{}%'.format(value))


def ends_with(field, value):
    return functions.Cast(field, SqlTypes.VARCHAR).like('%{}'.format(value))


def insensitive_contains(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper('%{}%'.format(value))
    )


def insensitive_starts_with(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper('{}%'.format(value))
    )


def insensitive_ends_with(field, value):
    return functions.Upper(functions.Cast(field, SqlTypes.VARCHAR)).like(
        functions.Upper('%{}'.format(value))
    )


def get_m2m_filters(field_name: str, field: fields.ManyToManyField) -> dict:
    filters = {
        field_name: {
            'field': field.forward_key,
            'backward_key': field.backward_key,
            'operator': operator.eq,
            'table': Table(field.through),
        },
        '{}__not'.format(field_name): {
            'field': field.forward_key,
            'backward_key': field.backward_key,
            'operator': not_equal,
            'table': Table(field.through),
        },
        '{}__in'.format(field_name): {
            'field': field.forward_key,
            'backward_key': field.backward_key,
            'operator': is_in,
            'table': Table(field.through),
            'value_encoder': list,
        },
        '{}__not_in'.format(field_name): {
            'field': field.forward_key,
            'backward_key': field.backward_key,
            'operator': not_in,
            'table': Table(field.through),
            'value_encoder': list,
        },
    }
    return filters


def get_backward_fk_filters(field_name: str, field: fields.BackwardFKRelation) -> dict:
    filters = {
        field_name: {
            'field': 'id',
            'backward_key': field.relation_field,
            'operator': operator.eq,
            'table': Table(field.type._meta.table),
        },
        '{}__not'.format(field_name): {
            'field': 'id',
            'backward_key': field.relation_field,
            'operator': not_equal,
            'table': Table(field.type._meta.table),
        },
        '{}__in'.format(field_name): {
            'field': 'id',
            'backward_key': field.relation_field,
            'operator': is_in,
            'table': Table(field.type._meta.table),
            'value_encoder': list,
        },
        '{}__not_in'.format(field_name): {
            'field': 'id',
            'backward_key': field.relation_field,
            'operator': not_in,
            'table': Table(field.type._meta.table),
            'value_encoder': list,
        },
    }
    return filters


def get_filters_for_field(field_name: str, field: Optional[fields.Field], source_field: str):
    if isinstance(field, fields.ManyToManyField):
        return get_m2m_filters(field_name, field)
    if isinstance(field, fields.BackwardFKRelation):
        return get_backward_fk_filters(field_name, field)
    filters = {
        field_name: {
            'field': source_field,
            'operator': operator.eq,
        },
        '{}__not'.format(field_name): {
            'field': source_field,
            'operator': not_equal,
        },
        '{}__in'.format(field_name): {
            'field': source_field,
            'operator': is_in,
            'value_encoder': list,
        },
        '{}__not_in'.format(field_name): {
            'field': source_field,
            'operator': not_in,
            'value_encoder': list,
        },
        '{}__isnull'.format(field_name): {
            'field': source_field,
            'operator': is_null,
        },
        '{}__not_isnull'.format(field_name): {
            'field': source_field,
            'operator': not_null,
        },
        '{}__gte'.format(field_name): {
            'field': source_field,
            'operator': operator.ge,
        },
        '{}__lte'.format(field_name): {
            'field': source_field,
            'operator': operator.le,
        },
        '{}__gt'.format(field_name): {
            'field': source_field,
            'operator': operator.gt,
        },
        '{}__lt'.format(field_name): {
            'field': source_field,
            'operator': operator.lt,
        },
        '{}__contains'.format(field_name): {
            'field': source_field,
            'operator': contains,
        },
        '{}__startswith'.format(field_name): {
            'field': source_field,
            'operator': starts_with,
        },
        '{}__endswith'.format(field_name): {
            'field': source_field,
            'operator': ends_with,
        },
        '{}__icontains'.format(field_name): {
            'field': source_field,
            'operator': insensitive_contains,
        },
        '{}__istartswith'.format(field_name): {
            'field': source_field,
            'operator': insensitive_starts_with,
        },
        '{}__iendswith'.format(field_name): {
            'field': source_field,
            'operator': insensitive_ends_with,
        },
    }
    return filters


class MetaInfo:
    __slots__ = ('abstract', 'table', 'app', 'fields', 'db_fields', 'm2m_fields', 'fk_fields',
                 'backward_fk_fields', 'fetch_fields', 'fields_db_projection', '_inited',
                 'fields_db_projection_reverse', 'filters', 'fields_map', 'default_connection')

    def __init__(self, meta):
        self.abstract = getattr(meta, 'abstract', False)  # type: bool
        self.table = getattr(meta, 'table', None)  # type: Optional[Table]
        self.app = getattr(meta, 'app', None)  # type: Optional[str]
        self.fields = set()  # type: Set[str]
        self.db_fields = set()  # type: Set[str]
        self.m2m_fields = set()  # type: Set[str]
        self.fk_fields = set()  # type: Set[str]
        self.backward_fk_fields = set()  # type: Set[str]
        self.fetch_fields = set()  # type: Set[str]
        self.fields_db_projection = {}  # type: Dict[str,str]
        self.fields_db_projection_reverse = {}  # type: Dict[str,str]
        self.filters = {}  # type: Dict[str, Dict[str, dict]]
        self.fields_map = {}  # type: Dict[str, fields.Field]
        self._inited = False
        self.default_connection = None

    @property
    def db(self):
        from tortoise import Tortoise
        if self.default_connection not in current_transaction_map:
            return None
        return (
            current_transaction_map[self.default_connection].get()
            or Tortoise.get_connection(self.default_connection)
        )

    def get_filter(self, key):
        filter_info = self.filters[key]
        overridden_operator = self.db.executor_class.get_overridden_filter_func(
            filter_func=filter_info['operator'],
        )
        if overridden_operator:
            filter_info = deepcopy(filter_info)
            filter_info['operator'] = overridden_operator
        return filter_info


class ModelMeta(type):
    def __new__(mcs, name, bases, attrs, *args, **kwargs):
        fields_db_projection = {}  # type: Dict[str,str]
        fields_map = {}  # type: Dict[str, fields.Field]
        filters = {}  # type: Dict[str, Dict[str, dict]]
        fk_fields = set()  # type: Set[str]
        m2m_fields = set()  # type: Set[str]

        if 'id' not in attrs:
            attrs['id'] = fields.IntField(pk=True)

        for key, value in attrs.items():
            if isinstance(value, fields.Field):
                fields_map[key] = value
                if isinstance(value, fields.ForeignKeyField):
                    key_field = '{}_id'.format(key)
                    value.source_field = key_field
                    fields_db_projection[key_field] = key_field
                    fields_map[key_field] = fields.IntField(
                        reference=value,
                        null=value.null,
                        default=value.default,
                    )
                    filters.update(
                        get_filters_for_field(
                            field_name=key_field,
                            field=fields_map[key_field],
                            source_field=key_field,
                        )
                    )
                    fk_fields.add(key)
                elif isinstance(value, fields.ManyToManyField):
                    m2m_fields.add(key)
                else:
                    fields_db_projection[key] = value.source_field if value.source_field else key
                    filters.update(
                        get_filters_for_field(
                            field_name=key,
                            field=fields_map[key],
                            source_field=fields_db_projection[key]
                        )
                    )

        attrs['_meta'] = meta = MetaInfo(attrs.get('Meta'))

        meta.fields_map = fields_map
        meta.fields_db_projection = fields_db_projection
        meta.fields_db_projection_reverse = {
            value: key
            for key, value in fields_db_projection.items()
        }
        meta.fields = set(fields_map.keys())
        meta.db_fields = set(fields_db_projection.values())
        meta.filters = filters
        meta.fk_fields = fk_fields
        meta.backward_fk_fields = set()
        meta.m2m_fields = m2m_fields
        meta.fetch_fields = fk_fields | m2m_fields
        meta.default_connection = None
        meta._inited = False
        if not fields_map:
            meta.abstract = True

        new_class = super().__new__(mcs, name, bases, attrs)
        return new_class


class Model(metaclass=ModelMeta):
    # TODO: I don' like this here, but it makes autocompletion and static analysis much happier
    _meta = MetaInfo(None)
    id = None  # type: Optional[Hashable]

    def __init__(self, *args, **kwargs) -> None:
        is_new = not bool(kwargs.get('id'))

        for key, field in self._meta.fields_map.items():
            if isinstance(field, fields.BackwardFKRelation):
                setattr(
                    self, key,
                    RelationQueryContainer(field.type, field.relation_field, self, is_new)
                )
            elif isinstance(field, fields.ManyToManyField):
                setattr(self, key, ManyToManyRelationManager(field.type, self, field, is_new))
            elif isinstance(field, fields.Field):
                setattr(self, key, field.default)
            else:
                setattr(self, key, None)

        passed_fields = set(kwargs.keys())
        for key, value in kwargs.items():
            if key in self._meta.fk_fields:
                if hasattr(value, 'id') and not value.id:
                    raise OperationalError(
                        'You should first call .save() on {} before referring to it'.format(value))
                relation_field = '{}_id'.format(key)
                setattr(self, relation_field, value.id)
                passed_fields.add(relation_field)
            elif key in self._meta.backward_fk_fields:
                raise ConfigurationError(
                    'You can\'t set backward relations through init, change related model instead'
                )
            elif key in self._meta.m2m_fields:
                raise ConfigurationError(
                    'You can\'t set m2m relations through init, use m2m_manager instead'
                )
            elif key in self._meta.fields:
                field_object = self._meta.fields_map[key]
                if value is None and not field_object.null:
                    raise ValueError('{} is non nullable field, but null was passed'.format(key))
                setattr(self, key, field_object.to_python_value(value))
            elif key in self._meta.db_fields:
                setattr(self, self._meta.fields_db_projection_reverse[key], value)

        for key, field_object in self._meta.fields_map.items():
            if key in passed_fields or key in self._meta.fetch_fields:
                continue
            else:
                if callable(field_object.default):
                    setattr(self, key, field_object.default())
                else:
                    setattr(self, key, field_object.default)

    async def _insert_instance(self, using_db=None) -> None:
        db = using_db if using_db else self._meta.db
        await db.executor_class(
            model=self.__class__,
            db=db,
        ).execute_insert(self)

    async def _update_instance(self, using_db=None) -> None:
        db = using_db if using_db else self._meta.db
        await db.executor_class(
            model=self.__class__,
            db=db,
        ).execute_update(self)

    async def save(self, *args, **kwargs) -> None:
        if not self.id:
            await self._insert_instance(*args, **kwargs)
        else:
            await self._update_instance(*args, **kwargs)

    async def delete(self, using_db=None) -> None:
        db = using_db if using_db else self._meta.db
        if not self.id:
            raise OperationalError("Can't delete unpersisted record")
        await db.executor_class(
            model=self.__class__,
            db=db,
        ).execute_delete(self)

    async def fetch_related(self, *args, using_db=None):
        db = using_db if using_db else self._meta.db
        await db.executor_class(
            model=self.__class__,
            db=db,
        ).fetch_for_list([self], *args)

    def __str__(self) -> str:
        return '<{}>'.format(self.__class__.__name__)

    def __repr__(self) -> str:
        if self.id:
            return '<{}: {}>'.format(self.__class__.__name__, self.id)
        return '<{}>'.format(self.__class__.__name__)

    def __hash__(self):
        if not self.id:
            raise TypeError('Model instances without id are unhashable')
        return hash(self.id)

    def __eq__(self, other) -> bool:
        # pylint: disable=C0123
        if type(self) == type(other) and self.id == other.id:
            return True
        return False

    @classmethod
    async def get_or_create(
        cls: Type[MODEL_TYPE],
        using_db=None,
        defaults=None,
        **kwargs
    ) -> Tuple[MODEL_TYPE, bool]:
        if not defaults:
            defaults = {}
        instance = await cls.filter(**kwargs).first()
        if instance:
            return instance, False
        return await cls.create(**defaults, **kwargs, using_db=using_db), True

    @classmethod
    async def create(cls: Type[MODEL_TYPE], **kwargs) -> MODEL_TYPE:
        instance = cls(**kwargs)
        await instance.save(using_db=kwargs.get('using_db'))
        return instance

    @classmethod
    def first(cls) -> QuerySet:
        return QuerySet(cls).first()

    @classmethod
    def filter(cls, *args, **kwargs) -> QuerySet:
        return QuerySet(cls).filter(*args, **kwargs)

    @classmethod
    def all(cls) -> QuerySet:
        return QuerySet(cls)

    @classmethod
    def get(cls, *args, **kwargs) -> QuerySet:
        return QuerySet(cls).get(*args, **kwargs)

    @classmethod
    async def fetch_for_list(cls, instance_list, *args, using_db=None):
        db = using_db if using_db else cls._meta.db
        await db.executor_class(
            model=cls,
            db=db,
        ).fetch_for_list(instance_list, *args)

    class Meta:
        pass
