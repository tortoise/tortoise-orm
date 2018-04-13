import decimal

import datetime

from pypika import Table

from tortoise.exceptions import NoValuesFetched
from tortoise.utils import AsyncIteratorWrapper


CASCADE = 'CASCADE'
RESTRICT = 'RESTRICT'
SET_NULL = 'SET NULL'
SET_DEFAULT = 'SET DEFAULT'


class Field:
    def __init__(self, type=None, source_field=None, generated=False, pk=False,
                 null=False, default=None, unique=False, *args, **kwargs):
        self.type = type
        self.source_field = source_field
        self.generated = generated
        self.pk = pk
        self.default = default
        self.null = null
        self.unique = unique


class IntField(Field):
    def __init__(self, source_field=None, pk=False, *args, **kwargs):
        kwargs['generated'] = bool(kwargs.get('generated')) | pk
        super().__init__(int, source_field, *args, **kwargs)
        self.reference = kwargs.get('reference')
        self.pk = pk


class SmallIntField(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(int, *args, **kwargs)


class CharField(Field):
    def __init__(self, max_length, *args, **kwargs):
        self.max_length = int(max_length)
        assert self.max_length > 0
        super().__init__(str, *args, **kwargs)


class TextField(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(str, *args, **kwargs)


class BooleanField(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(bool, *args, **kwargs)


class DecimalField(Field):
    def __init__(self, max_digits, decimal_places, *args, **kwargs):
        assert int(max_digits) >= 0 and int(decimal_places) >= 0
        super().__init__(decimal.Decimal, *args, **kwargs)
        self.max_digits = max_digits
        self.decimal_places = decimal_places


class DatetimeField(Field):
    def __init__(self, auto_now=False, auto_now_add=False, *args, **kwargs):
        assert not (auto_now_add and auto_now), 'You can choose only auto_now or auto_now_add'
        auto_now_add = auto_now_add | auto_now
        kwargs['generated'] = bool(kwargs.get('generated')) | auto_now_add
        super().__init__(datetime.datetime, *args, **kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add


class DateField(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(datetime.date, *args, **kwargs)


class FloatField(Field):
    def __init__(self, *args, **kwargs):
        super().__init__(float, *args, **kwargs)


class ForeignKeyField(Field):
    def __init__(self, model_name, related_name=None, on_delete=CASCADE, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(model_name, str) and len(model_name.split(".")) == 2, \
            'Foreign key accepts model name in format "app.Model"'
        self.model_name = model_name
        self.related_name = related_name
        assert on_delete in {CASCADE, RESTRICT, SET_NULL}
        assert (on_delete == SET_NULL) == bool(kwargs.get('null'))
        self.on_delete = on_delete


class ManyToManyField(Field):
    def __init__(self, model_name, through, forward_key=None, backward_key=None, related_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert len(model_name.split(".")) == 2, 'Foreign key accepts model name in format "app.Model"'
        self.model_name = model_name
        self.related_name = related_name
        self.forward_key = forward_key if forward_key else '{}_id'.format(model_name.split(".")[1].lower())
        self.backward_key = backward_key
        self.through = through
        self._generated = False


class BackwardFKRelation:
    def __init__(self, type, relation_field, *args, **kwargs):
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
        assert self.instance.id, (
            "This objects hasn't been instanced, call .save() before calling related queries"
        )
        return self.model.filter(**{self.relation_field: self.instance.id})

    def __contains__(self, item):
        if not self._fetched:
            raise NoValuesFetched('No values were fetched for this relation, first use .fetch_related()')
        return item in self.related_objects

    def __iter__(self):
        if not self._fetched:
            raise NoValuesFetched('No values were fetched for this relation, first use .fetch_related()')
        return self.related_objects.__iter__()

    def __len__(self):
        if not self._fetched:
            raise NoValuesFetched('No values were fetched for this relation, first use .fetch_related()')
        return len(self.related_objects)

    def __bool__(self):
        if not self._fetched:
            raise NoValuesFetched('No values were fetched for this relation, first use .fetch_related()')
        return bool(self.related_objects)

    def __getitem__(self, item):
        if not self._fetched:
            raise NoValuesFetched('No values were fetched for this relation, first use .fetch_related()')
        return self.related_objects[item]

    async def __aiter__(self):
        self.related_objects = await self._query
        self._fetched = True
        return AsyncIteratorWrapper(self.related_objects)

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
        for item in sequence:
            assert isinstance(item, self.model)
        self._fetched = True
        self.related_objects = sequence


class ManyToManyRelationManager(RelationQueryContainer):
    def __init__(self, model, instance, m2m_field, is_new):
        super().__init__(model, m2m_field.related_name, instance, is_new)
        self.field = m2m_field
        self.model = m2m_field.type
        self.instance = instance
        self._db = self.model._meta.db

    async def add(self, *instances, using_db=None):
        if not instances:
            return
        db = using_db if using_db else self._db
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
        select_query = select_query.where(
            criterion
        )

        already_existing_relations_raw = await db.execute_query(str(select_query))
        already_existing_relations = set(
            (r[self.field.backward_key], r[self.field.forward_key]) for r in already_existing_relations_raw
        )

        insert_is_required = False
        for instance_to_add in instances:
            if (self.instance.id, instance_to_add.id) in already_existing_relations:
                continue
            query = query.insert(instance_to_add.id, self.instance.id)
            insert_is_required = True
        if insert_is_required:
            await db.execute_query(str(query))

    async def clear(self, using_db=None):
        db = using_db if using_db else self._db
        through_table = Table(self.field.through)
        query = db.query_class.from_(through_table).where(
            getattr(through_table, self.field.backward_key) == self.instance.id
        ).delete()
        await db.execute_query(str(query))

    async def remove(self, *instances, using_db=None):
        db = using_db if using_db else self._db
        assert instances
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
        query = db.query_class.from_(through_table).where(
            condition
        ).delete()
        await db.execute_query(str(query))


StringField = TextField
