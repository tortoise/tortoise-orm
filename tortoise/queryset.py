import types
from copy import copy
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generator,
    Generic,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from pypika import JoinType, Order, Table
from pypika.functions import Cast, Count
from pypika.queries import QueryBuilder
from pypika.terms import Case, Field, Term, ValueWrapper
from typing_extensions import Protocol

from tortoise.backends.base.client import BaseDBAsyncClient, Capabilities
from tortoise.exceptions import (
    DoesNotExist,
    FieldError,
    IntegrityError,
    MultipleObjectsReturned,
    ParamsError,
)
from tortoise.expressions import Expression, F, Q, RawSQL
from tortoise.fields.relational import (
    ForeignKeyFieldInstance,
    OneToOneFieldInstance,
    RelationalField,
)
from tortoise.functions import Function
from tortoise.query_utils import Prefetch, QueryModifier, _get_joins_for_related_field
from tortoise.router import router
from tortoise.utils import chunk

# Empty placeholder - Should never be edited.

QUERY: QueryBuilder = QueryBuilder()

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model

MODEL = TypeVar("MODEL", bound="Model")
T_co = TypeVar("T_co", covariant=True)


class QuerySetSingle(Protocol[T_co]):
    """
    Awaiting on this will resolve a single instance of the Model object, and not a sequence.
    """

    # pylint: disable=W0104
    def __await__(self) -> Generator[Any, None, T_co]:
        ...  # pragma: nocoverage

    def prefetch_related(self, *args: Union[str, Prefetch]) -> "QuerySetSingle[MODEL]":
        ...  # pragma: nocoverage

    def select_related(self, *args: str) -> "QuerySetSingle[MODEL]":
        ...  # pragma: nocoverage

    def annotate(self, **kwargs: Function) -> "QuerySetSingle[MODEL]":
        ...  # pragma: nocoverage

    def only(self, *fields_for_select: str) -> "QuerySetSingle[MODEL]":
        ...  # pragma: nocoverage

    def values_list(self, *fields_: str, flat: bool = False) -> "ValuesListQuery":
        ...  # pragma: nocoverage

    def values(self, *args: str, **kwargs: str) -> "ValuesQuery":
        ...  # pragma: nocoverage


class AwaitableQuery(Generic[MODEL]):
    __slots__ = ("_joined_tables", "query", "model", "_db", "capabilities", "_annotations")

    def __init__(self, model: Type[MODEL]) -> None:
        self._joined_tables: List[Table] = []
        self.model: "Type[Model]" = model
        self.query: QueryBuilder = QUERY
        self._db: BaseDBAsyncClient = None  # type: ignore
        self.capabilities: Capabilities = model._meta.db.capabilities
        self._annotations: Dict[str, Expression] = {}

    def _choose_db(self, for_write: bool = False) -> BaseDBAsyncClient:
        """
        Return the connection that will be used if this query is executed now.

        :return: BaseDBAsyncClient:
        """
        if self._db:
            return self._db
        if for_write:
            db = router.db_for_write(self.model)
        else:
            db = router.db_for_read(self.model)
        return db or self.model._meta.db

    def resolve_filters(
        self,
        model: "Type[Model]",
        q_objects: List[Q],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Builds the common filters for a QuerySet.

        :param model: The Model this queryset is based on.
        :param q_objects: The Q expressions to apply.
        :param annotations: Extra annotations to add.
        :param custom_filters: Pre-resolved filters to be passed through.
        """
        has_aggregate = self._resolve_annotate()

        modifier = QueryModifier()
        for node in q_objects:
            node._annotations = annotations
            node._custom_filters = custom_filters
            modifier &= node.resolve(model, model._meta.basetable)

        where_criterion, joins, having_criterion = modifier.get_query_modifiers()
        for join in joins:
            if join[0] not in self._joined_tables:
                self.query = self.query.join(join[0], how=JoinType.left_outer).on(join[1])
                self._joined_tables.append(join[0])

        self.query._wheres = where_criterion
        self.query._havings = having_criterion

        if has_aggregate and (self._joined_tables or having_criterion or self.query._orderbys):
            self.query = self.query.groupby(
                *[self.model._meta.basetable[field] for field in self.model._meta.db_fields]
            )

    def _join_table_by_field(
        self, table: Table, related_field_name: str, related_field: RelationalField
    ) -> Table:
        joins = _get_joins_for_related_field(table, related_field, related_field_name)
        for join in joins:
            if join[0] not in self._joined_tables:
                self.query = self.query.join(join[0], how=JoinType.left_outer).on(join[1])
                self._joined_tables.append(join[0])
        return joins[-1][0]

    @staticmethod
    def _resolve_ordering_string(ordering: str) -> Tuple[str, Order]:
        order_type = Order.asc
        if ordering[0] == "-":
            field_name = ordering[1:]
            order_type = Order.desc
        else:
            field_name = ordering

        return field_name, order_type

    def resolve_ordering(
        self,
        model: "Type[Model]",
        table: Table,
        orderings: Iterable[Tuple[str, str]],
        annotations: Dict[str, Any],
    ) -> None:
        """
        Applies standard ordering to QuerySet.

        :param model: The Model this queryset is based on.
        :param table: ``pypika.Table`` to keep track of the virtual SQL table
            (to allow self referential joins)
        :param orderings: What columns/order to order by
        :param annotations:  Annotations that may be ordered on

        :raises FieldError: If a field provided does not exist in model.
        """
        # Do not apply default ordering for annotated queries to not mess them up
        if not orderings and self.model._meta.ordering and not annotations:
            orderings = self.model._meta.ordering

        for ordering in orderings:
            field_name = ordering[0]
            if field_name in model._meta.fetch_fields:
                raise FieldError(
                    "Filtering by relation is not possible. Filter by nested field of related model"
                )

            related_field_name, __, forwarded = field_name.partition("__")
            if related_field_name in model._meta.fetch_fields:
                related_field = cast(RelationalField, model._meta.fields_map[related_field_name])
                related_table = self._join_table_by_field(table, related_field_name, related_field)
                self.resolve_ordering(
                    related_field.related_model,
                    related_table,
                    [(forwarded, ordering[1])],
                    {},
                )
            elif field_name in annotations:
                annotation = annotations[field_name]
                if isinstance(annotation, Term):
                    self.query = self.query.orderby(annotation, order=ordering[1])
                else:
                    annotation_info = annotation.resolve(self.model, table)
                    self.query = self.query.orderby(annotation_info["field"], order=ordering[1])
            else:
                field_object = model._meta.fields_map.get(field_name)

                if not field_object:
                    raise FieldError(f"Unknown field {field_name} for model {model.__name__}")
                field_name = field_object.source_field or field_name
                field = table[field_name]

                func = field_object.get_for_dialect(
                    model._meta.db.capabilities.dialect, "function_cast"
                )
                if func:
                    field = func(field_object, field)

                self.query = self.query.orderby(field, order=ordering[1])

    def _resolve_annotate(self) -> bool:
        if not self._annotations:
            return False

        table = self.model._meta.basetable
        annotation_info = {}
        for key, annotation in self._annotations.items():
            if isinstance(annotation, Term):
                annotation_info[key] = {"joins": [], "field": annotation}
            else:
                annotation_info[key] = annotation.resolve(self.model, table)

        for key, info in annotation_info.items():
            for join in info["joins"]:
                self._join_table_by_field(*join)
            self.query._select_other(info["field"].as_(key))

        return any(info["field"].is_aggregate for info in annotation_info.values())

    def sql(self, **kwargs) -> str:
        """Return the actual SQL."""
        return self.as_query().get_sql(**kwargs)

    def as_query(self) -> QUERY:
        """Return the actual query."""
        if self._db is None:
            self._db = self._choose_db()  # type: ignore
        self._make_query()
        return self.query

    def _make_query(self) -> None:
        raise NotImplementedError()  # pragma: nocoverage

    async def _execute(self) -> Any:
        raise NotImplementedError()  # pragma: nocoverage


class QuerySet(AwaitableQuery[MODEL]):
    __slots__ = (
        "fields",
        "_prefetch_map",
        "_prefetch_queries",
        "_single",
        "_raise_does_not_exist",
        "_db",
        "_limit",
        "_offset",
        "_fields_for_select",
        "_filter_kwargs",
        "_orderings",
        "_q_objects",
        "_distinct",
        "_having",
        "_custom_filters",
        "_group_bys",
        "_select_for_update",
        "_select_for_update_nowait",
        "_select_for_update_skip_locked",
        "_select_for_update_of",
        "_select_related",
        "_select_related_idx",
        "_use_indexes",
        "_force_indexes",
    )

    def __init__(self, model: Type[MODEL]) -> None:
        super().__init__(model)
        self.fields: Set[str] = model._meta.db_fields
        self._prefetch_map: Dict[str, Set[Union[str, Prefetch]]] = {}
        self._prefetch_queries: Dict[str, List[Tuple[Optional[str], QuerySet]]] = {}
        self._single: bool = False
        self._raise_does_not_exist: bool = False
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._filter_kwargs: Dict[str, Any] = {}
        self._orderings: List[Tuple[str, Any]] = []
        self._q_objects: List[Q] = []
        self._distinct: bool = False
        self._having: Dict[str, Any] = {}
        self._custom_filters: Dict[str, dict] = {}
        self._fields_for_select: Tuple[str, ...] = ()
        self._group_bys: Tuple[str, ...] = ()
        self._select_for_update: bool = False
        self._select_for_update_nowait: bool = False
        self._select_for_update_skip_locked: bool = False
        self._select_for_update_of: Set[str] = set()
        self._select_related: Set[str] = set()
        self._select_related_idx: List[
            Tuple["Type[Model]", int, str, "Type[Model]", Iterable[Optional[str]]]
        ] = []  # format with: model,idx,model_name,parent_model
        self._force_indexes: Set[str] = set()
        self._use_indexes: Set[str] = set()

    def _clone(self) -> "QuerySet[MODEL]":
        queryset = self.__class__.__new__(self.__class__)
        queryset.fields = self.fields
        queryset.model = self.model
        queryset.query = self.query
        queryset.capabilities = self.capabilities
        queryset._prefetch_map = copy(self._prefetch_map)
        queryset._prefetch_queries = copy(self._prefetch_queries)
        queryset._single = self._single
        queryset._raise_does_not_exist = self._raise_does_not_exist
        queryset._db = self._db
        queryset._limit = self._limit
        queryset._offset = self._offset
        queryset._fields_for_select = self._fields_for_select
        queryset._filter_kwargs = copy(self._filter_kwargs)
        queryset._orderings = copy(self._orderings)
        queryset._joined_tables = copy(self._joined_tables)
        queryset._q_objects = copy(self._q_objects)
        queryset._distinct = self._distinct
        queryset._annotations = copy(self._annotations)
        queryset._having = copy(self._having)
        queryset._custom_filters = copy(self._custom_filters)
        queryset._group_bys = copy(self._group_bys)
        queryset._select_for_update = self._select_for_update
        queryset._select_for_update_nowait = self._select_for_update_nowait
        queryset._select_for_update_skip_locked = self._select_for_update_skip_locked
        queryset._select_for_update_of = self._select_for_update_of
        queryset._select_related = self._select_related
        queryset._select_related_idx = self._select_related_idx
        queryset._force_indexes = self._force_indexes
        queryset._use_indexes = self._use_indexes
        return queryset

    def _filter_or_exclude(self, *args: Q, negate: bool, **kwargs: Any) -> "QuerySet[MODEL]":
        queryset = self._clone()
        for arg in args:
            if not isinstance(arg, Q):
                raise TypeError("expected Q objects as args")
            if negate:
                queryset._q_objects.append(~arg)
            else:
                queryset._q_objects.append(arg)

        for key, value in kwargs.items():
            if negate:
                queryset._q_objects.append(~Q(**{key: value}))
            else:
                queryset._q_objects.append(Q(**{key: value}))

        return queryset

    def filter(self, *args: Q, **kwargs: Any) -> "QuerySet[MODEL]":
        """
        Filters QuerySet by given kwargs. You can filter by related objects like this:

        .. code-block:: python3

            Team.filter(events__tournament__name='Test')

        You can also pass Q objects to filters as args.
        """
        return self._filter_or_exclude(negate=False, *args, **kwargs)

    def exclude(self, *args: Q, **kwargs: Any) -> "QuerySet[MODEL]":
        """
        Same as .filter(), but with appends all args with NOT
        """
        return self._filter_or_exclude(negate=True, *args, **kwargs)

    def order_by(self, *orderings: str) -> "QuerySet[MODEL]":
        """
        Accept args to filter by in format like this:

        .. code-block:: python3

            .order_by('name', '-tournament__name')

        Supports ordering by related models too.
        A '-' before the name will result in descending sort order, default is ascending.

        :raises FieldError: If unknown field has been provided.
        """
        queryset = self._clone()
        new_ordering = []
        for ordering in orderings:
            field_name, order_type = self._resolve_ordering_string(ordering)

            if not (
                field_name.split("__")[0] in self.model._meta.fields
                or field_name in self._annotations
            ):
                raise FieldError(f"Unknown field {field_name} for model {self.model.__name__}")
            new_ordering.append((field_name, order_type))
        queryset._orderings = new_ordering
        return queryset

    def limit(self, limit: int) -> "QuerySet[MODEL]":
        """
        Limits QuerySet to given length.

        :raises ParamsError: Limit should be non-negative number.
        """
        if limit < 0:
            raise ParamsError("Limit should be non-negative number")

        queryset = self._clone()
        queryset._limit = limit
        return queryset

    def offset(self, offset: int) -> "QuerySet[MODEL]":
        """
        Query offset for QuerySet.

        :raises ParamsError: Offset should be non-negative number.
        """
        if offset < 0:
            raise ParamsError("Offset should be non-negative number")

        queryset = self._clone()
        queryset._offset = offset
        if self.capabilities.requires_limit and queryset._limit is None:
            queryset._limit = 1000000
        return queryset

    def distinct(self) -> "QuerySet[MODEL]":
        """
        Make QuerySet distinct.

        Only makes sense in combination with a ``.values()`` or ``.values_list()`` as it
        precedes all the fetched fields with a distinct.
        """
        queryset = self._clone()
        queryset._distinct = True
        return queryset

    def select_for_update(
        self, nowait: bool = False, skip_locked: bool = False, of: Tuple[str, ...] = ()
    ) -> "QuerySet[MODEL]":
        """
        Make QuerySet select for update.

        Returns a queryset that will lock rows until the end of the transaction,
        generating a SELECT ... FOR UPDATE SQL statement on supported databases.
        """
        if self.capabilities.support_for_update:
            queryset = self._clone()
            queryset._select_for_update = True
            queryset._select_for_update_nowait = nowait
            queryset._select_for_update_skip_locked = skip_locked
            queryset._select_for_update_of = set(of)
            return queryset
        return self

    def annotate(self, **kwargs: Union[Expression, Term]) -> "QuerySet[MODEL]":
        """
        Annotate result with aggregation or function result.

        :raises TypeError: Value of kwarg is expected to be a ``Function`` instance.
        """
        from tortoise.models import get_filters_for_field

        queryset = self._clone()
        for key, annotation in kwargs.items():
            # if not isinstance(annotation, (Function, Term)):
            #     raise TypeError("value is expected to be Function/Term instance")
            queryset._annotations[key] = annotation
            queryset._custom_filters.update(get_filters_for_field(key, None, key))
        return queryset

    def group_by(self, *fields: str) -> "QuerySet[MODEL]":
        """
        Make QuerySet returns list of dict or tuple with group by.

        Must call before .values() or .values_list()
        """
        queryset = self._clone()
        queryset._group_bys = fields
        return queryset

    def values_list(self, *fields_: str, flat: bool = False) -> "ValuesListQuery":
        """
        Make QuerySet returns list of tuples for given args instead of objects.

        If call after `.get()`, `.get_or_none()` or `.first()` return tuples for given args instead of object.

        If ```flat=True`` and only one arg is passed can return flat list or just scalar.

        If no arguments are passed it will default to a tuple containing all fields
        in order of declaration.
        """
        return ValuesListQuery(
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            flat=flat,
            fields_for_select_list=fields_  # type: ignore
            or [
                field
                for field in self.model._meta.fields_map.keys()
                if field in self.model._meta.db_fields
            ]
            + list(self._annotations.keys()),
            distinct=self._distinct,
            limit=self._limit,
            offset=self._offset,
            orderings=self._orderings,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            group_bys=self._group_bys,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
        )

    def values(self, *args: str, **kwargs: str) -> "ValuesQuery":
        """
        Make QuerySet return dicts instead of objects.

        If call after `.get()`, `.get_or_none()` or `.first()` return dict instead of object.

        Can pass names of fields to fetch, or as a ``field_name='name_in_dict'`` kwarg.

        If no arguments are passed it will default to a dict containing all fields.

        :raises FieldError: If duplicate key has been provided.
        """
        if args or kwargs:
            fields_for_select: Dict[str, str] = {}
            for field in args:
                if field in fields_for_select:
                    raise FieldError(f"Duplicate key {field}")
                fields_for_select[field] = field

            for return_as, field in kwargs.items():
                if return_as in fields_for_select:
                    raise FieldError(f"Duplicate key {return_as}")
                fields_for_select[return_as] = field
        else:
            _fields = [
                field
                for field in self.model._meta.fields_map.keys()
                if field in self.model._meta.fields_db_projection.keys()
            ] + list(self._annotations.keys())

            fields_for_select = {field: field for field in _fields}

        return ValuesQuery(
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            single=self._single,
            raise_does_not_exist=self._raise_does_not_exist,
            fields_for_select=fields_for_select,
            distinct=self._distinct,
            limit=self._limit,
            offset=self._offset,
            orderings=self._orderings,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            group_bys=self._group_bys,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
        )

    def delete(self) -> "DeleteQuery":
        """
        Delete all objects in QuerySet.
        """
        return DeleteQuery(
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
        )

    def update(self, **kwargs: Any) -> "UpdateQuery":
        """
        Update all objects in QuerySet with given kwargs.

        .. admonition: Example:

            .. code-block:: py3

                await Employee.filter(occupation='developer').update(salary=5000)

        Will instead of returning a resultset, update the data in the DB itself.
        """
        return UpdateQuery(
            db=self._db,
            model=self.model,
            update_kwargs=kwargs,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
        )

    def count(self) -> "CountQuery":
        """
        Return count of objects in queryset instead of objects.
        """
        return CountQuery(
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            offset=self._offset,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
        )

    def exists(self) -> "ExistsQuery":
        """
        Return True/False whether queryset exists.
        """
        return ExistsQuery(
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            force_indexes=self._force_indexes,
            use_indexes=self._use_indexes,
        )

    def all(self) -> "QuerySet[MODEL]":
        """
        Return the whole QuerySet.
        Essentially a no-op except as the only operation.
        """
        return self._clone()

    def raw(self, sql: str) -> "RawSQLQuery":
        """
        Return the QuerySet from raw SQL
        """
        return RawSQLQuery(model=self.model, db=self._db, sql=sql)

    def first(self) -> QuerySetSingle[Optional[MODEL]]:
        """
        Limit queryset to one object and return one object instead of list.
        """
        queryset = self._clone()
        queryset._limit = 1
        queryset._single = True
        return queryset  # type: ignore

    def get(self, *args: Q, **kwargs: Any) -> QuerySetSingle[MODEL]:
        """
        Fetch exactly one object matching the parameters.
        """
        queryset = self.filter(*args, **kwargs)
        queryset._limit = 2
        queryset._single = True
        queryset._raise_does_not_exist = True
        return queryset  # type: ignore

    async def in_bulk(
        self, id_list: Iterable[Union[str, int]], field_name: str
    ) -> Dict[str, MODEL]:
        """
        Return a dictionary mapping each of the given IDs to the object with
        that ID. If `id_list` isn't provided, evaluate the entire QuerySet.

        :param id_list: A list of field values
        :param field_name: Must be a unique field
        """
        objs = await self.filter(**{f"{field_name}__in": id_list})
        return {getattr(obj, field_name): obj for obj in objs}

    def bulk_create(
        self,
        objects: Iterable[MODEL],
        batch_size: Optional[int] = None,
        ignore_conflicts: bool = False,
        update_fields: Optional[Iterable[str]] = None,
        on_conflict: Optional[Iterable[str]] = None,
    ) -> "BulkCreateQuery":
        """
        This method inserts the provided list of objects into the database in an efficient manner
        (generally only 1 query, no matter how many objects there are),
        and returns created objects as a list, in the same order as provided

        :param on_conflict: On conflict index name
        :param update_fields: Update fields when conflicts
        :param ignore_conflicts: Ignore conflicts when inserting
        :param objects: List of objects to bulk create
        :param batch_size: How many objects are created in a single query

        :raises ValueError: If params do not meet specifications
        """
        if ignore_conflicts and update_fields:
            raise ValueError(
                "ignore_conflicts and update_fields are mutually exclusive.",
            )
        if not ignore_conflicts:
            if (update_fields and not on_conflict) or (on_conflict and not update_fields):
                raise ValueError("update_fields and on_conflict need set in same time.")
        return BulkCreateQuery(  # type:ignore
            db=self._db,
            model=self.model,
            objects=objects,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_fields=update_fields,
            on_conflict=on_conflict,
        )

    def bulk_update(
        self,
        objects: Iterable[MODEL],
        fields: Iterable[str],
        batch_size: Optional[int] = None,
    ) -> "BulkUpdateQuery":
        """
        Update the given fields in each of the given objects in the database.

        :param objects: List of objects to bulk create
        :param fields: The fields to update
        :param batch_size: How many objects are created in a single query

        :raises ValueError: If objects have no primary key set
        """
        if any(obj.pk is None for obj in objects):
            raise ValueError("All bulk_update() objects must have a primary key set.")
        return BulkUpdateQuery(  # type:ignore
            db=self._db,
            model=self.model,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            limit=self._limit,
            orderings=self._orderings,
            objects=objects,
            fields=fields,
            batch_size=batch_size,
        )

    def get_or_none(self, *args: Q, **kwargs: Any) -> QuerySetSingle[Optional[MODEL]]:
        """
        Fetch exactly one object matching the parameters.
        """
        queryset = self.filter(*args, **kwargs)
        queryset._limit = 2
        queryset._single = True
        return queryset  # type: ignore

    def only(self, *fields_for_select: str) -> "QuerySet[MODEL]":
        """
        Fetch ONLY the specified fields to create a partial model.

        Persisting changes on the model is allowed only when:

        * All the fields you want to update is specified in ``<model>.save(update_fields=[...])``
        * You included the Model primary key in the `.only(...)``

        To protect against common mistakes we ensure that errors get raised:

        * If you access a field that is not specified, you will get an ``AttributeError``.
        * If you do a ``<model>.save()`` a ``IncompleteInstanceError`` will be raised as the model is, as requested, incomplete.
        * If you do a ``<model>.save(update_fields=[...])`` and you didn't include the primary key in the ``.only(...)``,
          then ``IncompleteInstanceError`` will be raised indicating that updates can't be done without the primary key being known.
        * If you do a ``<model>.save(update_fields=[...])`` and one of the fields in ``update_fields`` was not in the ``.only(...)``,
          then ``IncompleteInstanceError`` as that field is not available to be updated.
        """
        queryset = self._clone()
        queryset._fields_for_select = fields_for_select
        return queryset

    def select_related(self, *fields: str) -> "QuerySet[MODEL]":
        """
        Return a new QuerySet instance that will select related objects.

        If fields are specified, they must be ForeignKey fields and only those
        related objects are included in the selection.
        """

        queryset = self._clone()
        for field in fields:
            queryset._select_related.add(field)
        return queryset

    def force_index(self, *index_names: str) -> "QuerySet[MODEL]":
        """
        The FORCE INDEX hint acts like USE INDEX (index_list),
        with the addition that a table scan is assumed to be very expensive.
        """
        if self.capabilities.support_index_hint:
            queryset = self._clone()
            for index_name in index_names:
                queryset._force_indexes.add(index_name)
            return queryset
        return self

    def use_index(self, *index_names: str) -> "QuerySet[MODEL]":
        """
        The USE INDEX (index_list) hint tells MySQL to use only one of the named indexes to find rows in the table.
        """
        if self.capabilities.support_index_hint:
            queryset = self._clone()
            for index_name in index_names:
                queryset._use_indexes.add(index_name)
            return queryset
        return self

    def prefetch_related(self, *args: Union[str, Prefetch]) -> "QuerySet[MODEL]":
        """
        Like ``.fetch_related()`` on instance, but works on all objects in QuerySet.

        :raises FieldError: If the field to prefetch on is not a relation, or not found.
        """
        queryset = self._clone()
        queryset._prefetch_map = {}

        for relation in args:
            if isinstance(relation, Prefetch):
                relation.resolve_for_queryset(queryset)
                continue

            first_level_field, __, forwarded_prefetch = relation.partition("__")
            if first_level_field not in self.model._meta.fetch_fields:
                if first_level_field in self.model._meta.fields:
                    raise FieldError(
                        f"Field {first_level_field} on {self.model._meta.full_name} is not a relation"
                    )
                raise FieldError(
                    f"Relation {first_level_field} for {self.model._meta.full_name} not found"
                )
            if first_level_field not in queryset._prefetch_map.keys():
                queryset._prefetch_map[first_level_field] = set()
            if forwarded_prefetch:
                queryset._prefetch_map[first_level_field].add(forwarded_prefetch)
        return queryset

    async def explain(self) -> Any:
        """Fetch and return information about the query execution plan.

        This is done by executing an ``EXPLAIN`` query whose exact prefix depends
        on the database backend, as documented below.

        - PostgreSQL: ``EXPLAIN (FORMAT JSON, VERBOSE) ...``
        - SQLite: ``EXPLAIN QUERY PLAN ...``
        - MySQL: ``EXPLAIN FORMAT=JSON ...``

        .. note::
            This is only meant to be used in an interactive environment for debugging
            and query optimization.
            **The output format may (and will) vary greatly depending on the database backend.**
        """
        if self._db is None:
            self._db = self._choose_db()  # type: ignore
        self._make_query()
        return await self._db.executor_class(model=self.model, db=self._db).execute_explain(
            self.query
        )

    def using_db(self, _db: BaseDBAsyncClient) -> "QuerySet[MODEL]":
        """
        Executes query in provided db client.
        Useful for transactions workaround.
        """
        queryset = self._clone()
        queryset._db = _db
        return queryset

    def _join_table_with_select_related(
        self,
        model: "Type[Model]",
        table: Table,
        field: str,
        forwarded_fields: str,
        path: Iterable[Optional[str]],
    ) -> Tuple[Table, str]:
        if field in model._meta.fields_db_projection and forwarded_fields:
            raise FieldError(f'Field "{field}" for model "{model.__name__}" is not relation')

        field_object = cast(RelationalField, model._meta.fields_map.get(field))
        if not field_object:
            raise FieldError(f'Unknown field "{field}" for model "{model.__name__}"')

        table = self._join_table_by_field(table, field, field_object)
        related_fields = field_object.related_model._meta.db_fields
        append_item = (field_object.related_model, len(related_fields), field, model, path)
        if append_item not in self._select_related_idx:
            self._select_related_idx.append(append_item)
        for related_field in related_fields:
            self.query = self.query.select(
                table[related_field].as_(f"{table.get_table_name()}.{related_field}")
            )
        if forwarded_fields:
            field, __, forwarded_fields_ = forwarded_fields.partition("__")
            self.query = self._join_table_with_select_related(
                model=field_object.related_model,
                table=table,
                field=field,
                forwarded_fields=forwarded_fields_,
                path=(*path, field),
            )
            return self.query
        return self.query

    def _make_query(self) -> None:
        # clean tmp records first
        self._select_related_idx = []
        self._joined_tables = []
        table = self.model._meta.basetable
        if self._fields_for_select:
            append_item = (self.model, len(self._fields_for_select), table, self.model, (None,))
            if append_item not in self._select_related_idx:
                self._select_related_idx.append(append_item)
            db_fields_for_select = [
                table[self.model._meta.fields_db_projection[field]].as_(field)
                for field in self._fields_for_select
            ]
            self.query = copy(self.model._meta.basequery).select(*db_fields_for_select)
        else:
            self.query = copy(self.model._meta.basequery_all_fields)
            append_item = (
                self.model,
                len(self.model._meta.db_fields) + len(self._annotations),
                table,
                self.model,
                (None,),
            )
            if append_item not in self._select_related_idx:
                self._select_related_idx.append(append_item)
        self.resolve_ordering(
            self.model, self.model._meta.basetable, self._orderings, self._annotations
        )
        self.resolve_filters(
            model=self.model,
            q_objects=self._q_objects,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
        )
        if self._limit:
            self.query._limit = self._limit
        if self._offset:
            self.query._offset = self._offset
        if self._distinct:
            self.query._distinct = True
        if self._select_for_update:
            self.query = self.query.for_update(
                self._select_for_update_nowait,
                self._select_for_update_skip_locked,
                self._select_for_update_of,
            )
        if self._select_related:
            for field in self._select_related:
                field, __, forwarded_fields = field.partition("__")
                self.query = self._join_table_with_select_related(
                    model=self.model,
                    table=self.model._meta.basetable,
                    field=field,
                    forwarded_fields=forwarded_fields,
                    path=(None, field),
                )
        if self._force_indexes:
            self.query._force_indexes = []
            self.query = self.query.force_index(*self._force_indexes)
        if self._use_indexes:
            self.query._use_indexes = []
            self.query = self.query.use_index(*self._use_indexes)

    def __await__(self) -> Generator[Any, None, List[MODEL]]:
        if self._db is None:
            self._db = self._choose_db(self._select_for_update)  # type: ignore
        self._make_query()
        return self._execute().__await__()

    async def __aiter__(self) -> AsyncIterator[MODEL]:
        for val in await self:
            yield val

    async def _execute(self) -> List[MODEL]:
        instance_list = await self._db.executor_class(
            model=self.model,
            db=self._db,
            prefetch_map=self._prefetch_map,
            prefetch_queries=self._prefetch_queries,
            select_related_idx=self._select_related_idx,
        ).execute_select(self.query, custom_fields=list(self._annotations.keys()))
        if self._single:
            if len(instance_list) == 1:
                return instance_list[0]
            if not instance_list:
                if self._raise_does_not_exist:
                    raise DoesNotExist("Object does not exist")
                return None  # type: ignore
            raise MultipleObjectsReturned("Multiple objects returned, expected exactly one")
        return instance_list


class UpdateQuery(AwaitableQuery):
    __slots__ = (
        "update_kwargs",
        "q_objects",
        "annotations",
        "custom_filters",
        "orderings",
        "limit",
        "values",
    )

    def __init__(
        self,
        model: Type[MODEL],
        update_kwargs: Dict[str, Any],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        limit: Optional[int],
        orderings: List[Tuple[str, str]],
    ) -> None:
        super().__init__(model)
        self.update_kwargs = update_kwargs
        self.q_objects = q_objects
        self.annotations = annotations
        self.custom_filters = custom_filters
        self._db = db
        self.limit = limit
        self.orderings = orderings
        self.values: List[Any] = []

    def _make_query(self) -> None:
        table = self.model._meta.basetable
        self.query = self._db.query_class.update(table)
        if self.capabilities.support_update_limit_order_by and self.limit:
            self.query._limit = self.limit
            self.resolve_ordering(self.model, table, self.orderings, self.annotations)

        self.resolve_filters(
            model=self.model,
            q_objects=self.q_objects,
            annotations=self.annotations,
            custom_filters=self.custom_filters,
        )
        # Need to get executor to get correct column_map
        executor = self._db.executor_class(model=self.model, db=self._db)
        count = 0
        for key, value in self.update_kwargs.items():
            field_object = self.model._meta.fields_map.get(key)
            if not field_object:
                raise FieldError(f"Unknown keyword argument {key} for model {self.model}")
            if field_object.pk:
                raise IntegrityError(f"Field {key} is PK and can not be updated")
            if isinstance(field_object, (ForeignKeyFieldInstance, OneToOneFieldInstance)):
                fk_field: str = field_object.source_field  # type: ignore
                db_field = self.model._meta.fields_map[fk_field].source_field
                value = executor.column_map[fk_field](
                    getattr(value, field_object.to_field_instance.model_field_name), None
                )
            else:
                try:
                    db_field = self.model._meta.fields_db_projection[key]
                except KeyError:
                    raise FieldError(f"Field {key} is virtual and can not be updated")
                if isinstance(value, Term):
                    value = F.resolver_arithmetic_expression(self.model, value)[0]
                elif isinstance(value, Function):
                    value = value.resolve(self.model, table)["field"]
                else:
                    value = executor.column_map[key](value, None)
            if isinstance(value, Term):
                self.query = self.query.set(db_field, value)
            else:
                self.query = self.query.set(db_field, executor.parameter(count))
                self.values.append(value)
                count += 1

    def __await__(self) -> Generator[Any, None, int]:
        if self._db is None:
            self._db = self._choose_db(True)  # type: ignore
        self._make_query()
        return self._execute().__await__()

    async def _execute(self) -> int:
        return (await self._db.execute_query(str(self.query), self.values))[0]


class DeleteQuery(AwaitableQuery):
    __slots__ = (
        "q_objects",
        "annotations",
        "custom_filters",
        "orderings",
        "limit",
    )

    def __init__(
        self,
        model: Type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        limit: Optional[int],
        orderings: List[Tuple[str, str]],
    ) -> None:
        super().__init__(model)
        self.q_objects = q_objects
        self.annotations = annotations
        self.custom_filters = custom_filters
        self._db = db
        self.limit = limit
        self.orderings = orderings

    def _make_query(self) -> None:
        self.query = copy(self.model._meta.basequery)
        if self.capabilities.support_update_limit_order_by and self.limit:
            self.query._limit = self.limit
            self.resolve_ordering(
                self.model, self.model._meta.basetable, self.orderings, self.annotations
            )
        self.resolve_filters(
            model=self.model,
            q_objects=self.q_objects,
            annotations=self.annotations,
            custom_filters=self.custom_filters,
        )
        self.query._delete_from = True

    def __await__(self) -> Generator[Any, None, int]:
        if self._db is None:
            self._db = self._choose_db(True)  # type: ignore
        self._make_query()
        return self._execute().__await__()

    async def _execute(self) -> int:
        return (await self._db.execute_query(str(self.query)))[0]


class ExistsQuery(AwaitableQuery):
    __slots__ = (
        "q_objects",
        "annotations",
        "custom_filters",
        "force_indexes",
        "use_indexes",
    )

    def __init__(
        self,
        model: Type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        force_indexes: Set[str],
        use_indexes: Set[str],
    ) -> None:
        super().__init__(model)
        self.q_objects = q_objects
        self.annotations = annotations
        self.custom_filters = custom_filters
        self._db = db
        self.force_indexes = force_indexes
        self.use_indexes = use_indexes

    def _make_query(self) -> None:
        self.query = copy(self.model._meta.basequery)
        self.resolve_filters(
            model=self.model,
            q_objects=self.q_objects,
            annotations=self.annotations,
            custom_filters=self.custom_filters,
        )
        self.query._limit = 1
        self.query._select_other(ValueWrapper(1))

        if self.force_indexes:
            self.query._force_indexes = []
            self.query = self.query.force_index(*self.force_indexes)
        if self.use_indexes:
            self.query._use_indexes = []
            self.query = self.query.use_index(*self.use_indexes)

    def __await__(self) -> Generator[Any, None, bool]:
        if self._db is None:
            self._db = self._choose_db()  # type: ignore
        self._make_query()
        return self._execute().__await__()

    async def _execute(self) -> bool:
        result, _ = await self._db.execute_query(str(self.query))
        return bool(result)


class CountQuery(AwaitableQuery):
    __slots__ = (
        "q_objects",
        "annotations",
        "custom_filters",
        "limit",
        "offset",
        "force_indexes",
        "use_indexes",
    )

    def __init__(
        self,
        model: Type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        limit: Optional[int],
        offset: Optional[int],
        force_indexes: Set[str],
        use_indexes: Set[str],
    ) -> None:
        super().__init__(model)
        self.q_objects = q_objects
        self.annotations = annotations
        self.custom_filters = custom_filters
        self.limit = limit
        self.offset = offset or 0
        self._db = db
        self.force_indexes = force_indexes
        self.use_indexes = use_indexes

    def _make_query(self) -> None:
        self.query = copy(self.model._meta.basequery)
        self.resolve_filters(
            model=self.model,
            q_objects=self.q_objects,
            annotations=self.annotations,
            custom_filters=self.custom_filters,
        )
        self.query._select_other(Count("*"))

        if self.force_indexes:
            self.query._force_indexes = []
            self.query = self.query.force_index(*self.force_indexes)
        if self.use_indexes:
            self.query._use_indexes = []
            self.query = self.query.use_index(*self.use_indexes)

    def __await__(self) -> Generator[Any, None, int]:
        if self._db is None:
            self._db = self._choose_db()  # type: ignore
        self._make_query()
        return self._execute().__await__()

    async def _execute(self) -> int:
        _, result = await self._db.execute_query(str(self.query))
        count = list(dict(result[0]).values())[0] - self.offset
        if self.limit and count > self.limit:
            return self.limit
        return count


class FieldSelectQuery(AwaitableQuery):
    # pylint: disable=W0223
    __slots__ = ("annotations",)

    def __init__(self, model: Type[MODEL], annotations: Dict[str, Any]) -> None:
        super().__init__(model)
        self.annotations = annotations

    def _join_table_with_forwarded_fields(
        self, model: Type[MODEL], table: Table, field: str, forwarded_fields: str
    ) -> Tuple[Table, str]:
        if field in model._meta.fields_db_projection and not forwarded_fields:
            return table, model._meta.fields_db_projection[field]

        if field in model._meta.fields_db_projection and forwarded_fields:
            raise FieldError(f'Field "{field}" for model "{model.__name__}" is not relation')

        if field in self.model._meta.fetch_fields and not forwarded_fields:
            raise ValueError(
                'Selecting relation "{}" is not possible, select concrete '
                "field on related model".format(field)
            )

        field_object = cast(RelationalField, model._meta.fields_map.get(field))
        if not field_object:
            raise FieldError(f'Unknown field "{field}" for model "{model.__name__}"')

        table = self._join_table_by_field(table, field, field_object)
        field, __, forwarded_fields_ = forwarded_fields.partition("__")

        return self._join_table_with_forwarded_fields(
            model=field_object.related_model,
            table=table,
            field=field,
            forwarded_fields=forwarded_fields_,
        )

    def add_field_to_select_query(self, field: str, return_as: str) -> None:
        table = self.model._meta.basetable

        if field in self.annotations:
            self._annotations[return_as] = self.annotations[field]
            return

        if field in self.model._meta.fields_db_projection:
            db_field = self.model._meta.fields_db_projection[field]
            self.query._select_field(table[db_field].as_(return_as))
            return

        if field in self.model._meta.fetch_fields:
            raise ValueError(
                'Selecting relation "{}" is not possible, select '
                "concrete field on related model".format(field)
            )

        field_, __, forwarded_fields = field.partition("__")
        if field_ in self.model._meta.fetch_fields:
            related_table, related_db_field = self._join_table_with_forwarded_fields(
                model=self.model,
                table=table,
                field=field_,
                forwarded_fields=forwarded_fields,
            )
            self.query._select_field(related_table[related_db_field].as_(return_as))
            return

        raise FieldError(f'Unknown field "{field}" for model "{self.model.__name__}"')

    def resolve_to_python_value(self, model: Type[MODEL], field: str) -> Callable:
        if field in model._meta.fetch_fields:
            # return as is to get whole model objects
            return lambda x: x

        if field in (x[1] for x in model._meta.db_native_fields):
            return lambda x: x

        if field in self.annotations:
            annotation = self.annotations[field]
            field_object = getattr(annotation, "field_object", None)
            if field_object:
                return field_object.to_python_value
            return lambda x: x

        if field in model._meta.fields_map:
            return model._meta.fields_map[field].to_python_value

        field_, __, forwarded_fields = field.partition("__")
        if field_ in model._meta.fetch_fields:
            new_model = model._meta.fields_map[field_].related_model  # type: ignore
            return self.resolve_to_python_value(new_model, forwarded_fields)

        raise FieldError(f'Unknown field "{field}" for model "{model}"')

    def _resolve_group_bys(self, *field_names: str):
        group_bys = []
        for field_name in field_names:
            if field_name in self._annotations:
                group_bys.append(Term(field_name))
                continue
            field, __, forwarded_fields = field_name.partition("__")
            related_table, related_db_field = self._join_table_with_forwarded_fields(
                model=self.model,
                table=self.model._meta.basetable,
                field=field,
                forwarded_fields=forwarded_fields,
            )
            field = related_table[related_db_field].as_(field_name)
            group_bys.append(field)
        return group_bys


class ValuesListQuery(FieldSelectQuery):
    __slots__ = (
        "flat",
        "fields",
        "limit",
        "offset",
        "distinct",
        "orderings",
        "annotations",
        "custom_filters",
        "q_objects",
        "single",
        "raise_does_not_exist",
        "fields_for_select_list",
        "group_bys",
        "force_indexes",
        "use_indexes",
    )

    def __init__(
        self,
        model: Type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select_list: List[str],
        limit: Optional[int],
        offset: Optional[int],
        distinct: bool,
        orderings: List[Tuple[str, str]],
        flat: bool,
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        group_bys: Tuple[str, ...],
        force_indexes: Set[str],
        use_indexes: Set[str],
    ) -> None:
        super().__init__(model, annotations)
        if flat and (len(fields_for_select_list) != 1):
            raise TypeError("You can flat value_list only if contains one field")

        fields_for_select = {str(i): field for i, field in enumerate(fields_for_select_list)}
        self.fields = fields_for_select
        self.limit = limit
        self.offset = offset
        self.distinct = distinct
        self.orderings = orderings
        self.custom_filters = custom_filters
        self.q_objects = q_objects
        self.single = single
        self.raise_does_not_exist = raise_does_not_exist
        self.fields_for_select_list = fields_for_select_list
        self.flat = flat
        self._db = db
        self.group_bys = group_bys
        self.force_indexes = force_indexes
        self.use_indexes = use_indexes

    def _make_query(self) -> None:
        self.query = copy(self.model._meta.basequery)
        for positional_number, field in self.fields.items():
            self.add_field_to_select_query(field, positional_number)

        self.resolve_ordering(
            self.model, self.model._meta.basetable, self.orderings, self.annotations
        )
        self.resolve_filters(
            model=self.model,
            q_objects=self.q_objects,
            annotations=self.annotations,
            custom_filters=self.custom_filters,
        )
        if self.limit:
            self.query._limit = self.limit
        if self.offset:
            self.query._offset = self.offset
        if self.distinct:
            self.query._distinct = True
        if self.group_bys:
            self.query._groupbys = self._resolve_group_bys(*self.group_bys)

        if self.force_indexes:
            self.query._force_indexes = []
            self.query = self.query.force_index(*self.force_indexes)
        if self.use_indexes:
            self.query._use_indexes = []
            self.query = self.query.use_index(*self.use_indexes)

    def __await__(self) -> Generator[Any, None, Union[List[Any], Tuple]]:
        if self._db is None:
            self._db = self._choose_db()  # type: ignore
        self._make_query()
        return self._execute().__await__()  # pylint: disable=E1101

    async def __aiter__(self) -> AsyncIterator[Any]:
        for val in await self:
            yield val

    async def _execute(self) -> Union[List[Any], Tuple]:
        _, result = await self._db.execute_query(str(self.query))
        columns = [
            (key, self.resolve_to_python_value(self.model, name))
            for key, name in sorted(self.fields.items())
        ]
        if self.flat:
            func = columns[0][1]
            flatmap = lambda entry: func(entry["0"])  # noqa
            lst_values = list(map(flatmap, result))
        else:
            listmap = lambda entry: tuple(func(entry[column]) for column, func in columns)  # noqa
            lst_values = list(map(listmap, result))

        if self.single:
            if len(lst_values) == 1:
                return lst_values[0]
            if not lst_values:
                if self.raise_does_not_exist:
                    raise DoesNotExist("Object does not exist")
                return None  # type: ignore
            raise MultipleObjectsReturned("Multiple objects returned, expected exactly one")
        return lst_values


class ValuesQuery(FieldSelectQuery):
    __slots__ = (
        "fields_for_select",
        "limit",
        "offset",
        "distinct",
        "orderings",
        "annotations",
        "custom_filters",
        "q_objects",
        "single",
        "raise_does_not_exist",
        "group_bys",
        "force_indexes",
        "use_indexes",
    )

    def __init__(
        self,
        model: Type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        single: bool,
        raise_does_not_exist: bool,
        fields_for_select: Dict[str, str],
        limit: Optional[int],
        offset: Optional[int],
        distinct: bool,
        orderings: List[Tuple[str, str]],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        group_bys: Tuple[str, ...],
        force_indexes: Set[str],
        use_indexes: Set[str],
    ) -> None:
        super().__init__(model, annotations)
        self.fields_for_select = fields_for_select
        self.limit = limit
        self.offset = offset
        self.distinct = distinct
        self.orderings = orderings
        self.custom_filters = custom_filters
        self.q_objects = q_objects
        self.single = single
        self.raise_does_not_exist = raise_does_not_exist
        self._db = db
        self.group_bys = group_bys
        self.force_indexes = force_indexes
        self.use_indexes = use_indexes

    def _make_query(self) -> None:
        self.query = copy(self.model._meta.basequery)
        for return_as, field in self.fields_for_select.items():
            self.add_field_to_select_query(field, return_as)

        self.resolve_ordering(
            self.model, self.model._meta.basetable, self.orderings, self.annotations
        )
        self.resolve_filters(
            model=self.model,
            q_objects=self.q_objects,
            annotations=self.annotations,
            custom_filters=self.custom_filters,
        )
        if self.limit:
            self.query._limit = self.limit
        if self.offset:
            self.query._offset = self.offset
        if self.distinct:
            self.query._distinct = True
        if self.group_bys:
            self.query._groupbys = self._resolve_group_bys(*self.group_bys)

        if self.force_indexes:
            self.query._force_indexes = []
            self.query = self.query.force_index(*self.force_indexes)
        if self.use_indexes:
            self.query._use_indexes = []
            self.query = self.query.use_index(*self.use_indexes)

    def __await__(self) -> Generator[Any, None, Union[List[dict], Dict]]:
        if self._db is None:
            self._db = self._choose_db()  # type: ignore
        self._make_query()
        return self._execute().__await__()  # pylint: disable=E1101

    async def __aiter__(self) -> AsyncIterator[dict]:
        for val in await self:
            yield val

    async def _execute(self) -> Union[List[dict], Dict]:
        result = await self._db.execute_query_dict(str(self.query))
        columns = [
            val
            for val in [
                (alias, self.resolve_to_python_value(self.model, field_name))
                for alias, field_name in self.fields_for_select.items()
            ]
            if not isinstance(val[1], types.LambdaType)
        ]

        if columns:
            for row in result:
                for col, func in columns:
                    row[col] = func(row[col])

        if self.single:
            if len(result) == 1:
                return result[0]
            if not result:
                if self.raise_does_not_exist:
                    raise DoesNotExist("Object does not exist")
                return None  # type: ignore
            raise MultipleObjectsReturned("Multiple objects returned, expected exactly one")
        return result


class RawSQLQuery(AwaitableQuery):
    __slots__ = ("_sql", "_db")

    def __init__(self, model: Type[MODEL], db: BaseDBAsyncClient, sql: str):
        super().__init__(model)
        self._sql = sql
        self._db = db

    def _make_query(self) -> None:
        self.query = RawSQL(self._sql)

    async def _execute(self) -> Any:
        instance_list = await self._db.executor_class(
            model=self.model,
            db=self._db,
        ).execute_select(self.query)
        return instance_list

    def __await__(self) -> Generator[Any, None, List[MODEL]]:
        if self._db is None:
            self._db = self._choose_db()  # type: ignore
        self._make_query()
        return self._execute().__await__()


class BulkUpdateQuery(UpdateQuery):
    __slots__ = ("objects", "fields", "batch_size", "queries")

    def __init__(
        self,
        model: Type[MODEL],
        db: BaseDBAsyncClient,
        q_objects: List[Q],
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        limit: Optional[int],
        orderings: List[Tuple[str, str]],
        objects: Iterable[MODEL],
        fields: Iterable[str],
        batch_size: Optional[int] = None,
    ):
        super().__init__(model, {}, db, q_objects, annotations, custom_filters, limit, orderings)
        self.objects = objects
        self.fields = fields
        self.batch_size = batch_size
        self.queries: List[QUERY] = []

    def _make_query(self) -> None:
        table = self.model._meta.basetable
        self.query = self._db.query_class.update(table)
        if self.capabilities.support_update_limit_order_by and self.limit:
            self.query._limit = self.limit
            self.resolve_ordering(self.model, table, self.orderings, self.annotations)

        self.resolve_filters(
            model=self.model,
            q_objects=self.q_objects,
            annotations=self.annotations,
            custom_filters=self.custom_filters,
        )
        executor = self._db.executor_class(model=self.model, db=self._db)
        pk_attr = self.model._meta.pk_attr
        pk = Field(pk_attr)
        for objects_item in chunk(self.objects, self.batch_size):
            query = copy(self.query)
            for field in self.fields:
                case = Case()
                pk_list = []
                for obj in objects_item:
                    value = executor.column_map[pk_attr](obj.pk, None)
                    field_value = getattr(obj, field)
                    case.when(
                        pk == value,
                        Cast(
                            self.query._wrapper_cls(field_value),
                            obj._meta.fields_map[field].get_for_dialect(
                                self._db.schema_generator.DIALECT, "SQL_TYPE"
                            ),
                        )
                        if self._db.schema_generator.DIALECT == "postgres"
                        else self.query._wrapper_cls(field_value),
                    )
                    pk_list.append(value)
                query = query.set(field, case)
                query = query.where(pk.isin(pk_list))
            self.queries.append(query)

    async def _execute(self) -> int:
        count = 0
        for query in self.queries:
            count += (await self._db.execute_query(str(query)))[0]
        return count

    def sql(self, **kwargs) -> str:
        self.as_query()
        return ";".join([str(query) for query in self.queries])


class BulkCreateQuery(AwaitableQuery):
    __slots__ = (
        "objects",
        "ignore_conflicts",
        "batch_size",
        "_db",
        "executor",
        "insert_query",
        "insert_query_all",
        "update_fields",
        "on_conflict",
    )

    def __init__(
        self,
        model: Type[MODEL],
        db: BaseDBAsyncClient,
        objects: Iterable[MODEL],
        batch_size: Optional[int] = None,
        ignore_conflicts: bool = False,
        update_fields: Optional[Iterable[str]] = None,
        on_conflict: Optional[Iterable[str]] = None,
    ):
        super().__init__(model)
        self.objects = list(objects)
        self.ignore_conflicts = ignore_conflicts
        self.batch_size = batch_size
        self._db = db
        self.update_fields = update_fields
        self.on_conflict = on_conflict

    def _make_query(self) -> None:
        self.executor = self._db.executor_class(model=self.model, db=self._db)
        if not self.ignore_conflicts and not self.update_fields:
            self.insert_query_all = self.executor.insert_query_all
            self.insert_query = self.executor.insert_query
        else:
            regular_columns, columns = self.executor._prepare_insert_columns()
            self.insert_query = self.executor._prepare_insert_statement(
                columns, ignore_conflicts=self.ignore_conflicts
            )
            self.insert_query_all = self.insert_query
            if self.model._meta.generated_db_fields:
                regular_columns_all, columns_all = self.executor._prepare_insert_columns(
                    include_generated=True
                )
                self.insert_query_all = self.executor._prepare_insert_statement(
                    columns_all, has_generated=False, ignore_conflicts=self.ignore_conflicts
                )
            if self.update_fields:
                alias = f"new_{self.model._meta.db_table}"
                self.insert_query_all = self.insert_query_all.as_(alias).on_conflict(  # type:ignore
                    *self.on_conflict
                )
                self.insert_query = self.insert_query.as_(alias).on_conflict(  # type:ignore
                    *self.on_conflict
                )
                for update_field in self.update_fields:
                    self.insert_query_all = self.insert_query_all.do_update(  # type:ignore
                        update_field
                    )
                    self.insert_query = self.insert_query.do_update(update_field)  # type:ignore

    async def _execute(self) -> List[MODEL]:
        for instance_chunk in chunk(self.objects, self.batch_size):
            values_lists_all = []
            values_lists = []
            for instance in instance_chunk:
                if instance._custom_generated_pk:
                    values_lists_all.append(
                        [
                            self.executor.column_map[field_name](
                                getattr(instance, field_name), instance
                            )
                            for field_name in self.executor.regular_columns_all
                        ]
                    )
                else:
                    values_lists.append(
                        [
                            self.executor.column_map[field_name](
                                getattr(instance, field_name), instance
                            )
                            for field_name in self.executor.regular_columns
                        ]
                    )
            if values_lists_all:
                await self._db.execute_many(str(self.insert_query_all), values_lists_all)
            if values_lists:
                await self._db.execute_many(str(self.insert_query), values_lists)
        return self.objects

    def __await__(self) -> Generator[Any, None, List[MODEL]]:
        if self._db is None:
            self._db = self._choose_db(True)  # type: ignore
        self._make_query()
        return self._execute().__await__()  # type: ignore

    def sql(self, **kwargs) -> str:
        self.as_query()
        if self.insert_query and self.insert_query_all:
            return ";".join([str(self.insert_query), str(self.insert_query_all)])
        return str(self.insert_query or self.insert_query_all)
