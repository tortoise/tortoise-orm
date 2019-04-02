from copy import copy
from typing import Dict, Hashable, List, Optional, Set, Tuple, Type, TypeVar, Union

from pypika import Query

from tortoise import fields
from tortoise.backends.base.client import BaseDBAsyncClient  # noqa
from tortoise.exceptions import ConfigurationError, OperationalError
from tortoise.fields import ManyToManyField, ManyToManyRelationManager, RelationQueryContainer
from tortoise.filters import get_filters_for_field
from tortoise.queryset import QuerySet
from tortoise.transactions import current_transaction_map

MODEL_TYPE = TypeVar("MODEL_TYPE", bound="Model")
# TODO: Define Filter type object. Possibly tuple?


def get_unique_together(meta):
    unique_together = getattr(meta, "unique_together", None)

    if isinstance(unique_together, (list, tuple)):
        if unique_together and isinstance(unique_together[0], str):
            unique_together = (unique_together,)

    # return without validation, validation will be done further in the code
    return unique_together


class MetaInfo:
    __slots__ = (
        "abstract",
        "table",
        "app",
        "fields",
        "db_fields",
        "m2m_fields",
        "fk_fields",
        "backward_fk_fields",
        "fetch_fields",
        "fields_db_projection",
        "_inited",
        "fields_db_projection_reverse",
        "filters",
        "fields_map",
        "default_connection",
        "basequery",
        "basequery_all_fields",
        "_filters",
        "unique_together",
    )

    def __init__(self, meta) -> None:
        self.abstract = getattr(meta, "abstract", False)  # type: bool
        self.table = getattr(meta, "table", "")  # type: str
        self.app = getattr(meta, "app", None)  # type: Optional[str]
        self.unique_together = get_unique_together(meta)  # type: Optional[Union[Tuple, List]]
        self.fields = set()  # type: Set[str]
        self.db_fields = set()  # type: Set[str]
        self.m2m_fields = set()  # type: Set[str]
        self.fk_fields = set()  # type: Set[str]
        self.backward_fk_fields = set()  # type: Set[str]
        self.fetch_fields = set()  # type: Set[str]
        self.fields_db_projection = {}  # type: Dict[str,str]
        self.fields_db_projection_reverse = {}  # type: Dict[str,str]
        self._filters = {}  # type: Dict[str, Dict[str, dict]]
        self.filters = {}  # type: Dict[str, dict]
        self.fields_map = {}  # type: Dict[str, fields.Field]
        self._inited = False  # type: bool
        self.default_connection = None  # type: Optional[str]
        self.basequery = Query()  # type: Query
        self.basequery_all_fields = Query()  # type: Query

    @property
    def db(self) -> BaseDBAsyncClient:
        try:
            return current_transaction_map[self.default_connection].get()
        except KeyError:
            raise ConfigurationError("No DB associated to model")

    def get_filter(self, key: str) -> dict:
        return self.filters[key]

    def generate_filters(self) -> None:
        get_overridden_filter_func = self.db.executor_class.get_overridden_filter_func
        for key, filter_info in self._filters.items():
            overridden_operator = get_overridden_filter_func(  # type: ignore
                filter_func=filter_info["operator"]
            )
            if overridden_operator:
                filter_info = copy(filter_info)
                filter_info["operator"] = overridden_operator  # type: ignore
            self.filters[key] = filter_info


class ModelMeta(type):
    __slots__ = ()

    def __new__(mcs, name: str, bases, attrs: dict, *args, **kwargs):
        fields_db_projection = {}  # type: Dict[str,str]
        fields_map = {}  # type: Dict[str, fields.Field]
        filters = {}  # type: Dict[str, Dict[str, dict]]
        fk_fields = set()  # type: Set[str]
        m2m_fields = set()  # type: Set[str]

        if "id" not in attrs:
            attrs["id"] = fields.IntField(pk=True)

        for key, value in attrs.items():
            if isinstance(value, fields.Field):
                fields_map[key] = value
                value.model_field_name = key
                if isinstance(value, fields.ForeignKeyField):
                    key_field = "{}_id".format(key)
                    value.source_field = key_field
                    fields_db_projection[key_field] = key_field
                    fields_map[key_field] = fields.IntField(
                        reference=value, null=value.null, default=value.default
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
                            source_field=fields_db_projection[key],
                        )
                    )

        attrs["_meta"] = meta = MetaInfo(attrs.get("Meta"))

        meta.fields_map = fields_map
        meta.fields_db_projection = fields_db_projection
        meta.fields_db_projection_reverse = {
            value: key for key, value in fields_db_projection.items()
        }
        meta.fields = set(fields_map.keys())
        meta.db_fields = set(fields_db_projection.values())
        meta._filters = filters
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
    # I don' like this here, but it makes autocompletion and static analysis much happier
    _meta = MetaInfo(None)
    id = None  # type: Optional[Hashable]

    def __init__(self, *args, **kwargs) -> None:
        # self._meta is a very common attribute lookup, lets cache it.
        meta = self._meta

        # Create lazy fk/m2m objects
        for key in meta.backward_fk_fields:
            field_object = meta.fields_map[key]
            setattr(
                self,
                key,
                RelationQueryContainer(
                    field_object.type, field_object.relation_field, self  # type: ignore
                ),
            )

        for key in meta.m2m_fields:
            field_object = meta.fields_map[key]
            setattr(
                self,
                key,
                ManyToManyRelationManager(  # type: ignore
                    field_object.type, self, field_object
                ),
            )

        # Assign values and do type conversions
        passed_fields = set(kwargs.keys())
        passed_fields.update(meta.fetch_fields)

        for key, value in kwargs.items():
            if key in meta.fk_fields:
                if hasattr(value, "id") and not value.id:
                    raise OperationalError(
                        "You should first call .save() on {} before referring to it".format(value)
                    )
                relation_field = "{}_id".format(key)
                setattr(self, relation_field, value.id)
                passed_fields.add(relation_field)
            elif key in meta.fields:
                field_object = meta.fields_map[key]
                if value is None and not field_object.null:
                    raise ValueError("{} is non nullable field, but null was passed".format(key))
                setattr(self, key, field_object.to_python_value(value))
            elif key in meta.db_fields:
                setattr(self, meta.fields_db_projection_reverse[key], value)
            elif key in meta.backward_fk_fields:
                raise ConfigurationError(
                    "You can't set backward relations through init, change related model instead"
                )
            elif key in meta.m2m_fields:
                raise ConfigurationError(
                    "You can't set m2m relations through init, use m2m_manager instead"
                )

        # Assign defaults for missing fields
        for key in meta.fields.difference(passed_fields):
            field_object = meta.fields_map[key]
            if callable(field_object.default):
                setattr(self, key, field_object.default())
            else:
                setattr(self, key, field_object.default)

    async def _insert_instance(self, using_db=None) -> None:
        db = using_db if using_db else self._meta.db
        await db.executor_class(model=self.__class__, db=db).execute_insert(self)

    async def _update_instance(self, using_db=None) -> None:
        db = using_db if using_db else self._meta.db
        await db.executor_class(model=self.__class__, db=db).execute_update(self)

    async def save(self, *args, **kwargs) -> None:
        if not self.id:
            await self._insert_instance(*args, **kwargs)
        else:
            await self._update_instance(*args, **kwargs)

    async def delete(self, using_db=None) -> None:
        db = using_db if using_db else self._meta.db
        if not self.id:
            raise OperationalError("Can't delete unpersisted record")
        await db.executor_class(model=self.__class__, db=db).execute_delete(self)

    async def fetch_related(self, *args, using_db=None):
        db = using_db if using_db else self._meta.db
        await db.executor_class(model=self.__class__, db=db).fetch_for_list([self], *args)

    def __str__(self) -> str:
        return "<{}>".format(self.__class__.__name__)

    def __repr__(self) -> str:
        if self.id:
            return "<{}: {}>".format(self.__class__.__name__, self.id)
        return "<{}>".format(self.__class__.__name__)

    def __hash__(self) -> int:
        if not self.id:
            raise TypeError("Model instances without id are unhashable")
        return hash(self.id)

    def __eq__(self, other) -> bool:
        # pylint: disable=C0123
        if type(self) == type(other) and self.id == other.id:
            return True
        return False

    @classmethod
    async def get_or_create(
        cls: Type[MODEL_TYPE], using_db=None, defaults=None, **kwargs
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
        await instance.save(using_db=kwargs.get("using_db"))
        return instance

    @classmethod
    def first(cls) -> QuerySet:
        return QuerySet(cls).first()

    @classmethod
    def filter(cls, *args, **kwargs) -> QuerySet:
        return QuerySet(cls).filter(*args, **kwargs)

    @classmethod
    def exclude(cls, *args, **kwargs) -> QuerySet:
        return QuerySet(cls).exclude(*args, **kwargs)

    @classmethod
    def annotate(cls, **kwargs) -> QuerySet:
        return QuerySet(cls).annotate(**kwargs)

    @classmethod
    def all(cls) -> QuerySet:
        return QuerySet(cls)

    @classmethod
    def get(cls, *args, **kwargs) -> QuerySet:
        return QuerySet(cls).get(*args, **kwargs)

    @classmethod
    async def fetch_for_list(cls, instance_list, *args, using_db=None):
        db = using_db if using_db else cls._meta.db
        await db.executor_class(model=cls, db=db).fetch_for_list(instance_list, *args)

    @classmethod
    def check(cls):
        cls._check_unique_together()

    @classmethod
    def _check_unique_together(cls):
        """Check the value of "unique_together" option."""
        if cls._meta.unique_together is None:
            return

        if not isinstance(cls._meta.unique_together, (tuple, list)):
            raise ConfigurationError(
                "'{}.unique_together' must be a list or tuple.".format(cls.__name__)
            )

        elif any(
            not isinstance(unique_fields, (tuple, list))
            for unique_fields in cls._meta.unique_together
        ):
            raise ConfigurationError(
                "All '{}.unique_together' elements must be lists or tuples.".format(cls.__name__)
            )

        else:
            for fields_tuple in cls._meta.unique_together:
                for field_name in fields_tuple:
                    field = cls._meta.fields_map.get(field_name)

                    if not field:
                        raise ConfigurationError(
                            "'{}.unique_together' has no '{}' "
                            "field.".format(cls.__name__, field_name)
                        )

                    if isinstance(field, ManyToManyField):
                        raise ConfigurationError(
                            "'{}.unique_together' '{}' field refers "
                            "to ManyToMany field.".format(cls.__name__, field_name)
                        )

    class Meta:
        pass
