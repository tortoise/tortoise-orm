from collections.abc import AsyncGenerator, Generator, Iterator
from typing import TYPE_CHECKING, Any, Generic, Optional, Type, TypeVar, Union, overload

from pypika_tortoise import Table
from typing_extensions import Literal

from tortoise.exceptions import ConfigurationError, NoValuesFetched, OperationalError
from tortoise.fields.base import CASCADE, SET_NULL, Field, OnDelete

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.backends.base.client import BaseDBAsyncClient
    from tortoise.models import Model
    from tortoise.queryset import Q, QuerySet

MODEL = TypeVar("MODEL", bound="Model")


class _NoneAwaitable:
    __slots__ = ()

    def __await__(self) -> Generator[None, None, None]:
        yield None

    def __bool__(self) -> bool:
        return False


NoneAwaitable = _NoneAwaitable()


class ReverseRelation(Generic[MODEL]):
    """
    Relation container for :func:`.ForeignKeyField`.
    """

    def __init__(
        self,
        remote_model: Type[MODEL],
        relation_field: str,
        instance: "Model",
        from_field: str,
    ) -> None:
        self.remote_model = remote_model
        self.relation_field = relation_field
        self.instance = instance
        self.from_field = from_field
        self._fetched = False
        self._custom_query = False
        self.related_objects: list[MODEL] = []

    @property
    def _query(self) -> "QuerySet[MODEL]":
        if not self.instance._saved_in_db:
            raise OperationalError(
                "This objects hasn't been instanced, call .save() before calling related queries"
            )
        return self.remote_model.filter(
            **{self.relation_field: getattr(self.instance, self.from_field)}
        )

    def __contains__(self, item: Any) -> bool:
        self._raise_if_not_fetched()
        return item in self.related_objects

    def __iter__(self) -> "Iterator[MODEL]":
        self._raise_if_not_fetched()
        return self.related_objects.__iter__()

    def __len__(self) -> int:
        self._raise_if_not_fetched()
        return len(self.related_objects)

    def __bool__(self) -> bool:
        self._raise_if_not_fetched()
        return bool(self.related_objects)

    def __getitem__(self, item: int) -> MODEL:
        self._raise_if_not_fetched()
        return self.related_objects[item]

    def __await__(self) -> Generator[Any, None, list[MODEL]]:
        return self._query.__await__()

    async def __aiter__(self) -> AsyncGenerator[Any, MODEL]:
        if not self._fetched:
            self._set_result_for_query(await self)
        for val in self.related_objects:
            yield val

    def filter(self, *args: "Q", **kwargs: Any) -> "QuerySet[MODEL]":
        """
        Returns a QuerySet with related elements filtered by args/kwargs.
        """
        return self._query.filter(*args, **kwargs)

    def all(self) -> "QuerySet[MODEL]":
        """
        Returns a QuerySet with all related elements.
        """
        return self._query

    def order_by(self, *orderings: str) -> "QuerySet[MODEL]":
        """
        Returns a QuerySet related elements in order.
        """
        return self._query.order_by(*orderings)

    def limit(self, limit: int) -> "QuerySet[MODEL]":
        """
        Returns a QuerySet with at most «limit» related elements.
        """
        return self._query.limit(limit)

    def offset(self, offset: int) -> "QuerySet[MODEL]":
        """
        Returns a QuerySet with all related elements offset by «offset».
        """
        return self._query.offset(offset)

    def _set_result_for_query(self, sequence: list[MODEL], attr: Optional[str] = None) -> None:
        self._fetched = True
        self.related_objects = sequence
        if attr:
            setattr(self.instance, attr, sequence)

    def _raise_if_not_fetched(self) -> None:
        if not self._fetched:
            raise NoValuesFetched(
                "No values were fetched for this relation, first use .fetch_related()"
            )


class ManyToManyRelation(ReverseRelation[MODEL]):
    """
    Many-to-many relation container for :func:`.ManyToManyField`.
    """

    def __init__(self, instance: "Model", m2m_field: "ManyToManyFieldInstance[MODEL]") -> None:
        super().__init__(m2m_field.related_model, m2m_field.related_name, instance, "pk")
        self.field = m2m_field
        self.instance = instance

    async def add(self, *instances: MODEL, using_db: "Optional[BaseDBAsyncClient]" = None) -> None:
        """
        Adds one or more of ``instances`` to the relation.

        If it is already added, it will be silently ignored.

        :raises OperationalError: If Object to add is not saved.
        """
        if not instances:
            return
        if not self.instance._saved_in_db:
            raise OperationalError(f"You should first call .save() on {self.instance}")
        db = using_db or self.remote_model._meta.db
        pk_formatting_func = type(self.instance)._meta.pk.to_db_value
        related_pk_formatting_func = type(instances[0])._meta.pk.to_db_value
        pk_b = pk_formatting_func(self.instance.pk, self.instance)
        pks_f: list = []
        for instance_to_add in instances:
            if not instance_to_add._saved_in_db:
                raise OperationalError(f"You should first call .save() on {instance_to_add}")
            pk_f = related_pk_formatting_func(instance_to_add.pk, instance_to_add)
            pks_f.append(pk_f)
        through_table = Table(self.field.through)
        backward_key, forward_key = self.field.backward_key, self.field.forward_key
        backward_field, forward_field = through_table[backward_key], through_table[forward_key]
        select_query = (
            db.query_class.from_(through_table).where(backward_field == pk_b).select(forward_key)
        )
        criterion = forward_field == pks_f[0] if len(pks_f) == 1 else forward_field.isin(pks_f)
        select_query = select_query.where(criterion)

        _, already_existing_relations_raw = await db.execute_query(
            *select_query.get_parameterized_sql()
        )
        already_existing_forward_pks = {
            related_pk_formatting_func(r[forward_key], self.instance)
            for r in already_existing_relations_raw
        }

        if pks_f_to_insert := set(pks_f) - already_existing_forward_pks:
            query = db.query_class.into(through_table).columns(forward_field, backward_field)
            for pk_f in pks_f_to_insert:
                query = query.insert(pk_f, pk_b)
            await db.execute_query(*query.get_parameterized_sql())

    async def clear(self, using_db: "Optional[BaseDBAsyncClient]" = None) -> None:
        """
        Clears ALL relations.
        """
        await self._remove_or_clear(using_db=using_db)

    async def remove(
        self, *instances: MODEL, using_db: "Optional[BaseDBAsyncClient]" = None
    ) -> None:
        """
        Removes one or more of ``instances`` from the relation.

        :raises OperationalError: remove() was called with no instances.
        """
        if not instances:
            raise OperationalError("remove() called on no instances")
        await self._remove_or_clear(instances, using_db)

    async def _remove_or_clear(
        self,
        instances: Optional[tuple[MODEL, ...]] = None,
        using_db: "Optional[BaseDBAsyncClient]" = None,
    ) -> None:
        db = using_db or self.remote_model._meta.db
        through_table = Table(self.field.through)
        pk_formatting_func = type(self.instance)._meta.pk.to_db_value

        condition = through_table[self.field.backward_key] == pk_formatting_func(
            self.instance.pk, self.instance
        )
        if instances:
            related_pk_formatting_func = type(instances[0])._meta.pk.to_db_value
            if len(instances) == 1:
                condition &= through_table[self.field.forward_key] == related_pk_formatting_func(
                    instances[0].pk, instances[0]
                )
            else:
                condition &= through_table[self.field.forward_key].isin(
                    [related_pk_formatting_func(i.pk, i) for i in instances]
                )
        query = db.query_class.from_(through_table).where(condition).delete()
        await db.execute_query(*query.get_parameterized_sql())


class RelationalField(Field[MODEL]):
    has_db_field = False

    def __init__(
        self,
        related_model: "Type[MODEL]",
        to_field: Optional[str] = None,
        db_constraint: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.related_model: "Type[MODEL]" = related_model
        self.to_field: str = to_field  # type: ignore
        self.to_field_instance: Field = None  # type: ignore
        self.db_constraint = db_constraint

    if TYPE_CHECKING:

        @overload
        def __get__(self, instance: None, owner: Type["Model"]) -> "RelationalField[MODEL]": ...

        @overload
        def __get__(self, instance: "Model", owner: Type["Model"]) -> MODEL: ...

        def __get__(
            self, instance: Optional["Model"], owner: Type["Model"]
        ) -> "RelationalField[MODEL] | MODEL": ...

        def __set__(self, instance: "Model", value: MODEL) -> None: ...

    def describe(self, serializable: bool) -> dict:
        desc = super().describe(serializable)
        desc["db_constraint"] = self.db_constraint
        del desc["db_column"]
        return desc

    @classmethod
    def validate_model_name(cls, model_name: str) -> None:
        if len(model_name.split(".")) != 2:
            field_type = cls.__name__.replace("Instance", "")
            raise ConfigurationError(f'{field_type} accepts model name in format "app.Model"')


class ForeignKeyFieldInstance(RelationalField[MODEL]):
    def __init__(
        self,
        model_name: str,
        related_name: Union[Optional[str], Literal[False]] = None,
        on_delete: OnDelete = CASCADE,
        **kwargs: Any,
    ) -> None:
        super().__init__(None, **kwargs)  # type: ignore
        self.validate_model_name(model_name)
        self.model_name = model_name
        self.related_name = related_name
        if on_delete not in set(OnDelete):
            raise ConfigurationError(
                "on_delete can only be CASCADE, RESTRICT, SET_NULL, SET_DEFAULT or NO_ACTION"
            )
        if on_delete == SET_NULL and not bool(kwargs.get("null")):
            raise ConfigurationError("If on_delete is SET_NULL, then field must have null=True set")
        self.on_delete = on_delete

    def describe(self, serializable: bool) -> dict:
        desc = super().describe(serializable)
        desc["raw_field"] = self.source_field
        desc["on_delete"] = str(self.on_delete)
        return desc


class BackwardFKRelation(RelationalField[MODEL]):
    def __init__(
        self,
        field_type: "Type[MODEL]",
        relation_field: str,
        relation_source_field: str,
        null: bool,
        description: Optional[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(field_type, null=null, **kwargs)
        self.relation_field: str = relation_field
        self.relation_source_field: str = relation_source_field
        self.description: Optional[str] = description


class OneToOneFieldInstance(ForeignKeyFieldInstance[MODEL]):
    def __init__(
        self,
        model_name: str,
        related_name: Union[Optional[str], Literal[False]] = None,
        on_delete: OnDelete = CASCADE,
        **kwargs: Any,
    ) -> None:
        self.validate_model_name(model_name)
        super().__init__(model_name, related_name, on_delete, unique=True, **kwargs)


class BackwardOneToOneRelation(BackwardFKRelation[MODEL]):
    pass


class ManyToManyFieldInstance(RelationalField[MODEL]):
    field_type = ManyToManyRelation

    def __init__(
        self,
        model_name: str,
        through: Optional[str] = None,
        forward_key: Optional[str] = None,
        backward_key: str = "",
        related_name: str = "",
        on_delete: OnDelete = CASCADE,
        field_type: "Type[MODEL]" = None,  # type: ignore
        create_unique_index: bool = True,
        **kwargs: Any,
    ) -> None:
        # TODO: rename through to through_table
        # TODO: add through to use a Model
        super().__init__(field_type, **kwargs)
        self.validate_model_name(model_name)
        self.model_name: str = model_name
        self.related_name: str = related_name
        self.forward_key: str = forward_key or f"{model_name.split('.')[1].lower()}_id"
        self.backward_key: str = backward_key
        self.through: str = through  # type: ignore
        self._generated: bool = False
        self.on_delete = on_delete
        self.create_unique_index = create_unique_index

    def describe(self, serializable: bool) -> dict:
        desc = super().describe(serializable)
        desc["model_name"] = self.model_name
        desc["related_name"] = self.related_name
        desc["forward_key"] = self.forward_key
        desc["backward_key"] = self.backward_key
        desc["through"] = self.through
        desc["on_delete"] = str(self.on_delete)
        desc["_generated"] = self._generated
        return desc


@overload
def OneToOneField(
    model_name: str,
    related_name: Union[Optional[str], Literal[False]] = None,
    on_delete: OnDelete = CASCADE,
    db_constraint: bool = True,
    *,
    null: Literal[True],
    **kwargs: Any,
) -> "OneToOneNullableRelation[MODEL]": ...


@overload
def OneToOneField(
    model_name: str,
    related_name: Union[Optional[str], Literal[False]] = None,
    on_delete: OnDelete = CASCADE,
    db_constraint: bool = True,
    null: Literal[False] = False,
    **kwargs: Any,
) -> "OneToOneRelation[MODEL]": ...


def OneToOneField(
    model_name: str,
    related_name: Union[Optional[str], Literal[False]] = None,
    on_delete: OnDelete = CASCADE,
    db_constraint: bool = True,
    null: bool = False,
    **kwargs: Any,
) -> "OneToOneRelation[MODEL] | OneToOneNullableRelation[MODEL]":
    """
    OneToOne relation field.

    This field represents a foreign key relation to another model.

    See :ref:`one_to_one` for usage information.

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
            ``field.NO_ACTION``:
                Take no action.
    ``to_field``:
        The attribute name on the related model to establish foreign key relationship.
        If not set, pk is used
    ``db_constraint``:
        Controls whether or not a constraint should be created in the database for this foreign key.
        The default is True, and that’s almost certainly what you want; setting this to False can be very bad for data integrity.
    """

    return OneToOneFieldInstance(
        model_name, related_name, on_delete, db_constraint=db_constraint, null=null, **kwargs
    )


@overload
def ForeignKeyField(
    model_name: str,
    related_name: Union[Optional[str], Literal[False]] = None,
    on_delete: OnDelete = CASCADE,
    db_constraint: bool = True,
    *,
    null: Literal[True],
    **kwargs: Any,
) -> "ForeignKeyNullableRelation[MODEL]": ...


@overload
def ForeignKeyField(
    model_name: str,
    related_name: Union[Optional[str], Literal[False]] = None,
    on_delete: OnDelete = CASCADE,
    db_constraint: bool = True,
    null: Literal[False] = False,
    **kwargs: Any,
) -> "ForeignKeyRelation[MODEL]": ...


def ForeignKeyField(
    model_name: str,
    related_name: Union[Optional[str], Literal[False]] = None,
    on_delete: OnDelete = CASCADE,
    db_constraint: bool = True,
    null: bool = False,
    **kwargs: Any,
) -> "ForeignKeyRelation[MODEL] | ForeignKeyNullableRelation[MODEL]":
    """
    ForeignKey relation field.

    This field represents a foreign key relation to another model.

    See :ref:`foreign_key` for usage information.

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
            ``field.NO_ACTION``:
                Take no action.
    ``to_field``:
        The attribute name on the related model to establish foreign key relationship.
        If not set, pk is used
    ``db_constraint``:
        Controls whether or not a constraint should be created in the database for this foreign key.
        The default is True, and that’s almost certainly what you want; setting this to False can be very bad for data integrity.
    """

    return ForeignKeyFieldInstance(
        model_name, related_name, on_delete, db_constraint=db_constraint, null=null, **kwargs
    )


def ManyToManyField(
    model_name: str,
    through: Optional[str] = None,
    forward_key: Optional[str] = None,
    backward_key: str = "",
    related_name: str = "",
    on_delete: OnDelete = CASCADE,
    db_constraint: bool = True,
    create_unique_index: bool = True,
    **kwargs: Any,
) -> "ManyToManyRelation[Any]":
    """
    ManyToMany relation field.

    This field represents a many-to-many between this model and another model.

    See :ref:`many_to_many` for usage information.

    You must provide the following:

    ``model_name``:
        The name of the related model in a :samp:`'{app}.{model}'` format.

    The following is optional:

    ``through``:
        The DB table that represents the through table.
        The default is normally safe.
    ``forward_key``:
        The forward lookup key on the through table.
        The default is normally safe.
    ``backward_key``:
        The backward lookup key on the through table.
        The default is normally safe.
    ``related_name``:
        The attribute name on the related model to reverse resolve the many to many.
    ``db_constraint``:
        Controls whether or not a constraint should be created in the database for this foreign key.
        The default is True, and that’s almost certainly what you want; setting this to False can be very bad for data integrity.
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
            ``field.NO_ACTION``:
                Take no action.
    ``create_unique_index``:
        Controls whether or not a unique index should be created in the database to speed up select queries.
        The default is True. If you want to allow repeat records, set this to False.
    """

    return ManyToManyFieldInstance(  # type: ignore
        model_name,
        through,
        forward_key,
        backward_key,
        related_name,
        on_delete=on_delete,
        db_constraint=db_constraint,
        create_unique_index=create_unique_index,
        **kwargs,
    )


OneToOneNullableRelation = Optional[OneToOneFieldInstance[MODEL]]
"""
Type hint for the result of accessing the :func:`.OneToOneField` field in the model
when obtained model can be nullable.
"""

OneToOneRelation = OneToOneFieldInstance[MODEL]
"""
Type hint for the result of accessing the :func:`.OneToOneField` field in the model.
"""

ForeignKeyNullableRelation = Optional[ForeignKeyFieldInstance[MODEL]]
"""
Type hint for the result of accessing the :func:`.ForeignKeyField` field in the model
when obtained model can be nullable.
"""

ForeignKeyRelation = ForeignKeyFieldInstance[MODEL]
"""
Type hint for the result of accessing the :func:`.ForeignKeyField` field in the model.
"""
