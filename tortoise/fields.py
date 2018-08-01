import datetime
import functools
import json
from decimal import Decimal
from typing import Any, Optional

from pypika import Table

import ciso8601
from tortoise.exceptions import ConfigurationError, NoValuesFetched, OperationalError
from tortoise.utils import QueryAsyncIterator

CASCADE = 'CASCADE'
RESTRICT = 'RESTRICT'
SET_NULL = 'SET NULL'
SET_DEFAULT = 'SET DEFAULT'

# Doing this we can replace json dumps/loads with different implementations
JSON_DUMPS = functools.partial(
    json.dumps,
    separators=(',', ':')
)
JSON_LOADS = json.loads


class Field:
    """
    Base Field type.
    """
    def __init__(
        self,
        type=None,
        source_field: Optional[str] = None,
        generated: bool = False,
        pk: bool = False,
        null: bool = False,
        default: Any = None,
        unique: bool = False,
        **kwargs
    ) -> None:
        self.type = type
        self.source_field = source_field
        self.generated = generated
        self.pk = pk
        self.default = default
        self.null = null
        self.unique = unique

    def to_db_value(self, value):
        return value

    def to_python_value(self, value):
        if value is None or isinstance(value, self.type):
            return value
        return self.type(value)


class IntField(Field):
    """
    Integer field.

    ``pk`` (bool):
        True if field is Primary Key.
    """
    def __init__(self, pk: bool = False, **kwargs) -> None:
        kwargs['generated'] = bool(kwargs.get('generated')) | pk
        super().__init__(int, **kwargs)
        self.reference = kwargs.get('reference')
        self.pk = pk


class SmallIntField(Field):
    """
    Small integer field.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(int, **kwargs)


class CharField(Field):
    """
    Character field.

    You must provide the following:

    ``max_length`` (int):
        Maximum length of the field in characters.
    """
    def __init__(self, max_length: int = 0, **kwargs) -> None:
        if int(max_length) < 1:
            raise ConfigurationError('max_digits must be >= 1')
        self.max_length = int(max_length)
        super().__init__(str, **kwargs)


class TextField(Field):
    """
    Large Text field.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(str, **kwargs)


class BooleanField(Field):
    """
    Boolean field.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(bool, **kwargs)


class DecimalField(Field):
    """
    Accurate decimal field.

    You must provide the following:

    ``max_digits`` (int):
        Max digits of significance of the decimal field.
    ``decimal_places`` (int):
        How many of those signifigant digits is after the decimal point.
    """
    def __init__(self, max_digits: int = 0, decimal_places: int = -1, **kwargs) -> None:
        if int(max_digits) < 1:
            raise ConfigurationError('max_digits must be >= 1')
        if int(decimal_places) < 0:
            raise ConfigurationError('decimal_places must be >= 0')
        super().__init__(Decimal, **kwargs)
        self.max_digits = max_digits
        self.decimal_places = decimal_places


class DatetimeField(Field):
    """
    Datetime field.

    ``auto_now`` and ``auto_now_add`` is exclusive.
    You can opt to set neither or only ONE of them.

    ``auto_now`` (bool):
        Always set to ``datetime.utcnow()`` on save.
    ``auto_now_add`` (bool):
        Set to ``datetime.utcnow()`` on first save only.
    """
    def __init__(self, auto_now: bool = False, auto_now_add: bool = False, **kwargs) -> None:
        if auto_now_add and auto_now:
            raise ConfigurationError('You can choose only auto_now or auto_now_add')
        auto_now_add = auto_now_add | auto_now
        kwargs['generated'] = bool(kwargs.get('generated')) | auto_now_add
        super().__init__(datetime.datetime, **kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def to_python_value(self, value):
        if value is None or isinstance(value, self.type):
            return value
        return ciso8601.parse_datetime(value)


class DateField(Field):
    """
    Date field.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(datetime.date, **kwargs)

    def to_python_value(self, value):
        if value is None or isinstance(value, self.type):
            return value
        return ciso8601.parse_datetime(value).date()


class FloatField(Field):
    """
    Float (double) field.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(float, **kwargs)


class JSONField(Field):
    """
    JSON field.

    This field can store dictionaries or lists of any JSON-compliant structure.

    ``encoder``:
        The JSON encoder. The default is recommemded.
    ``decoder``:
        The JSON decoder. The default is recommemded.
    """
    def __init__(self, encoder=JSON_DUMPS, decoder=JSON_LOADS, **kwargs) -> None:
        super().__init__((dict, list), **kwargs)
        self.encoder = encoder
        self.decoder = decoder

    def to_db_value(self, value):
        if value is None:
            return value
        return self.encoder(value)

    def to_python_value(self, value):
        if value is None or isinstance(value, self.type):
            return value
        return self.decoder(value)


class ForeignKeyField(Field):
    """
    ForeignKey relation field.

    This field represents a foreign key relation to another model.

    You must provide the following:

    ``model_name``:
        The name of the related model in a :samp:`'{app}.{model}'` format.

    The following is optional:

    ``related_name``:
        The attribute name on the related model to reverse resolve the foreign key.
    ``on_delete``:
        One of:
            ``field.CASCADE``:
                Indicate that the model should be cascade deleted if related model gets deleted.
            ``field.RESTRICT``:
                Indicate that the related model delete will be restricted as long as a
                foreign key points to it.
            ``field.SET_NULL``:
                Resets the field to NULL in case the related model gets deleted.
                Can only be set if field has ``null=True`` set.
            ``field.SET_DEFAULT``:
                Resets the field to ``default`` value in case the related model gets deleted.
                Can only be set is field has a ``default`` set.
    """
    def __init__(
        self,
        model_name: str,
        related_name: Optional[str] = None,
        on_delete=CASCADE,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        if isinstance(model_name, str) and len(model_name.split(".")) != 2:
            raise ConfigurationError('Foreign key accepts model name in format "app.Model"')
        self.model_name = model_name
        self.related_name = related_name
        if on_delete not in {CASCADE, RESTRICT, SET_NULL}:
            raise ConfigurationError('on_delete can only be CASCADE, RESTRICT or SET_NULL')
        if on_delete == SET_NULL and not bool(kwargs.get('null')):
            raise ConfigurationError('If on_delete is SET_NULL, then field must have null=True set')
        self.on_delete = on_delete


class ManyToManyField(Field):
    """
    ManyToMany relation field.

    This field represents a many-to-many between this model and another model.

    You must provide the following:

    ``model_name``:
        The name of the related model in a :samp:`'{app}.{model}'` format.

    The following is optional:

    ``through``:
        The DB table that represents the trough table.
        The default is normally safe.
    ``forward_key``:
        The forward lookup key on the through table.
        The default is normally safe.
    ``backward_key``:
        The backward lookup key on the through table.
        The default is normally safe.
    ``related_name``:
        The attribute name on the related model to reverse resolve the many to many.
    """
    def __init__(
        self,
        model_name: str,
        through: Optional[str] = None,
        forward_key: Optional[str] = None,
        backward_key: str = '',
        related_name: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        if len(model_name.split(".")) != 2:
            raise ConfigurationError('Foreign key accepts model name in format "app.Model"')
        self.model_name = model_name
        self.related_name = related_name
        self.forward_key = forward_key if forward_key else '{}_id'.format(
            model_name.split(".")[1].lower()
        )
        self.backward_key = backward_key
        self.through = through
        self._generated = False


class BackwardFKRelation:
    def __init__(self, type, relation_field, **kwargs):
        self.type = type
        self.relation_field = relation_field


class RelationQueryContainer:
    def __init__(self, model, relation_field, instance, is_new):
        self.model = model
        self.relation_field = relation_field
        self.instance = instance
        self._fetched = is_new
        self._custom_query = False
        self.related_objects = []

    @property
    def _query(self):
        if not self.instance.id:
            raise OperationalError("This objects hasn't been instanced, call .save() before"
                                   " calling related queries")
        return self.model.filter(**{self.relation_field: self.instance.id})

    def __contains__(self, item):
        if not self._fetched:
            raise NoValuesFetched(
                'No values were fetched for this relation, first use .fetch_related()'
            )
        return item in self.related_objects

    def __iter__(self):
        if not self._fetched:
            raise NoValuesFetched(
                'No values were fetched for this relation, first use .fetch_related()'
            )
        return self.related_objects.__iter__()

    def __len__(self):
        if not self._fetched:
            raise NoValuesFetched(
                'No values were fetched for this relation, first use .fetch_related()'
            )
        return len(self.related_objects)

    def __bool__(self):
        if not self._fetched:
            raise NoValuesFetched(
                'No values were fetched for this relation, first use .fetch_related()'
            )
        return bool(self.related_objects)

    def __getitem__(self, item):
        if not self._fetched:
            raise NoValuesFetched(
                'No values were fetched for this relation, first use .fetch_related()'
            )
        return self.related_objects[item]

    def __aiter__(self):
        async def fetched_callback(iterator_wrapper):
            self._fetched = True
            self.related_objects = iterator_wrapper.sequence

        return QueryAsyncIterator(self._query, callback=fetched_callback)

    def filter(self, *args, **kwargs):
        return self._query.filter(*args, **kwargs)

    def all(self):
        return self

    def order_by(self, *args, **kwargs):
        return self._query.order_by(*args, **kwargs)

    def limit(self, *args, **kwargs):
        return self._query.limit(*args, **kwargs)

    def offset(self, *args, **kwargs):
        return self._query.offset(*args, **kwargs)

    def distinct(self, *args, **kwargs):
        return self._query.distinct(*args, **kwargs)

    def _set_result_for_query(self, sequence):
        # TODO: What does this do?
        for item in sequence:
            if not isinstance(item, self.model):
                OperationalError("{} is not of {}".format(item, self.model))

        self._fetched = True
        self.related_objects = sequence


class ManyToManyRelationManager(RelationQueryContainer):
    def __init__(self, model, instance, m2m_field, is_new):
        super().__init__(model, m2m_field.related_name, instance, is_new)
        self.field = m2m_field
        self.model = m2m_field.type
        self.instance = instance

    async def add(self, *instances, using_db=None):
        if not instances:
            return
        db = using_db if using_db else self.model._meta.db
        through_table = Table(self.field.through)
        select_query = db.query_class.from_(through_table).where(
            getattr(through_table, self.field.backward_key) == self.instance.id
        ).select(self.field.backward_key, self.field.forward_key)
        query = db.query_class.into(through_table).columns(
            getattr(through_table, self.field.forward_key),
            getattr(through_table, self.field.backward_key),
        )
        criterion = getattr(through_table, self.field.forward_key) == instances[0].id
        for instance_to_add in instances[1:]:
            criterion |= getattr(through_table, self.field.forward_key) == instance_to_add.id
        select_query = select_query.where(criterion)

        already_existing_relations_raw = await db.execute_query(str(select_query))
        already_existing_relations = {(r[self.field.backward_key], r[self.field.forward_key])
                                      for r in already_existing_relations_raw}

        insert_is_required = False
        for instance_to_add in instances:
            if (self.instance.id, instance_to_add.id) in already_existing_relations:
                continue
            query = query.insert(instance_to_add.id, self.instance.id)
            insert_is_required = True
        if insert_is_required:
            await db.execute_query(str(query))

    async def clear(self, using_db=None):
        db = using_db if using_db else self.model._meta.db
        through_table = Table(self.field.through)
        query = db.query_class.from_(through_table).where(
            getattr(through_table, self.field.backward_key) == self.instance.id
        ).delete()
        await db.execute_query(str(query))

    async def remove(self, *instances, using_db=None):
        db = using_db if using_db else self.model._meta.db
        if not instances:
            raise OperationalError('remove() called on no instances')
        through_table = Table(self.field.through)
        condition = (
            getattr(through_table, self.field.forward_key) == instances[0].id
            & getattr(through_table, self.field.backward_key) == self.instance.id
        )
        for instance_to_remove in instances[1:]:
            condition |= (
                getattr(through_table, self.field.forward_key) == instance_to_remove.id
                & getattr(through_table, self.field.backward_key) == self.instance.id
            )
        query = db.query_class.from_(through_table).where(condition).delete()
        await db.execute_query(str(query))
