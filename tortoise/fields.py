import decimal

import datetime

from pypika import Table

from tortoise.exceptions import NoValuesFetched
from tortoise.utils import AsyncIteratorWrapper


class Field:
    def __init__(self, type=None, source_field=None, generated=False, pk=False, null=False, default=None):
        self.type = type
        self.source_field = source_field
        self.generated = generated
        self.pk = pk
        self.default = default


class IntField(Field):
    def __init__(self, source_field=None, *args, **kwargs):
        super().__init__(int, source_field, *args, **kwargs)


class StringField(Field):
    def __init__(self, source_field=None, *args, **kwargs):
        super().__init__(str, source_field, *args, **kwargs)


class BooleanField(Field):
    def __init__(self, source_field=None, *args, **kwargs):
        super().__init__(bool, source_field, *args, **kwargs)


class DecimalField(Field):
    def __init__(self, source_field=None, *args, **kwargs):
        super().__init__(decimal.Decimal, source_field, *args, **kwargs)


class DatetimeField(Field):
    def __init__(self, source_field=None, *args, **kwargs):
        super().__init__(datetime.datetime, source_field, *args, **kwargs)


class ForeignKeyField(Field):
    def __init__(self, model_name, related_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(model_name, str) and len(model_name.split(".")) == 2, \
            'Foreign key accepts model name in format "app.Model"'
        self.model_name = model_name
        self.related_name = related_name


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
        self._query = self.model.filter(**{self.relation_field: self.instance.id})
        self.related_objects = []

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
        db = using_db if using_db else self._db
        through_table = Table(self.field.through)
        query = db.query_class.into(through_table).columns(
            getattr(through_table, self.field.forward_key),
            getattr(through_table, self.field.backward_key),
        )
        for instance_to_add in instances:
            query = query.insert(instance_to_add.id, self.instance.id)
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
