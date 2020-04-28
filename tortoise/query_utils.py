from copy import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

from pypika import Table
from pypika.terms import Criterion

from tortoise.exceptions import FieldError, OperationalError
from tortoise.fields.relational import BackwardFKRelation, ManyToManyFieldInstance, RelationalField

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model
    from tortoise.queryset import QuerySet


def _process_filter_kwarg(
    model: "Type[Model]", key: str, value: Any, table: Table
) -> Tuple[Criterion, Optional[Tuple[Table, Criterion]]]:
    join = None

    if value is None and f"{key}__isnull" in model._meta.filters:
        param = model._meta.get_filter(f"{key}__isnull")
        value = True
    else:
        param = model._meta.get_filter(key)

    pk_db_field = model._meta.db_pk_column
    if param.get("table"):
        join = (
            param["table"],
            table[pk_db_field] == param["table"][param["backward_key"]],
        )
        if param.get("value_encoder"):
            value = param["value_encoder"](value, model)
        criterion = param["operator"](param["table"][param["field"]], value)
    else:
        field_object = model._meta.fields_map[param["field"]]
        encoded_value = (
            param["value_encoder"](value, model, field_object)
            if param.get("value_encoder")
            else model._meta.db.executor_class._field_to_db(field_object, value, model)
        )
        criterion = param["operator"](table[param["source_field"]], encoded_value)
    return criterion, join


def _get_joins_for_related_field(
    table: Table, related_field: RelationalField, related_field_name: str
) -> List[Tuple[Table, Criterion]]:
    required_joins = []

    related_table: Table = related_field.related_model._meta.basetable
    if isinstance(related_field, ManyToManyFieldInstance):
        through_table = Table(related_field.through)
        required_joins.append(
            (
                through_table,
                table[related_field.model._meta.db_pk_column]
                == through_table[related_field.backward_key],
            )
        )
        required_joins.append(
            (
                related_table,
                through_table[related_field.forward_key]
                == related_table[related_field.related_model._meta.db_pk_column],
            )
        )
    elif isinstance(related_field, BackwardFKRelation):
        to_field_source_field = (
            related_field.to_field_instance.source_field
            or related_field.to_field_instance.model_field_name
        )

        if table == related_table:
            related_table = related_table.as_(f"{table.get_table_name()}__{related_field_name}")
        required_joins.append(
            (
                related_table,
                table[to_field_source_field] == related_table[related_field.relation_source_field],
            )
        )
    else:
        to_field_source_field = (
            related_field.to_field_instance.source_field
            or related_field.to_field_instance.model_field_name
        )

        from_field = related_field.model._meta.fields_map[related_field.source_field]  # type: ignore
        from_field_source_field = from_field.source_field or from_field.model_field_name

        related_table = related_table.as_(f"{table.get_table_name()}__{related_field_name}")
        required_joins.append(
            (related_table, related_table[to_field_source_field] == table[from_field_source_field],)
        )
    return required_joins


class EmptyCriterion(Criterion):  # type: ignore
    def __or__(self, other: Criterion) -> Criterion:
        return other

    def __and__(self, other: Criterion) -> Criterion:
        return other

    def __bool__(self) -> bool:
        return False


def _and(left: Criterion, right: Criterion) -> Criterion:
    if left and not right:
        return left
    return left & right


def _or(left: Criterion, right: Criterion) -> Criterion:
    if left and not right:
        return left
    return left | right


class QueryModifier:
    """
    Internal structure used to generate SQL Queries.
    """

    def __init__(
        self,
        where_criterion: Optional[Criterion] = None,
        joins: Optional[List[Tuple[Table, Criterion]]] = None,
        having_criterion: Optional[Criterion] = None,
    ) -> None:
        self.where_criterion: Criterion = where_criterion or EmptyCriterion()
        self.joins = joins if joins else []
        self.having_criterion: Criterion = having_criterion or EmptyCriterion()

    def __and__(self, other: "QueryModifier") -> "QueryModifier":
        return QueryModifier(
            where_criterion=_and(self.where_criterion, other.where_criterion),
            joins=self.joins + other.joins,
            having_criterion=_and(self.having_criterion, other.having_criterion),
        )

    def __or__(self, other: "QueryModifier") -> "QueryModifier":
        if self.having_criterion or other.having_criterion:
            # TODO: This could be optimized?
            result_having_criterion = _or(
                _and(self.where_criterion, self.having_criterion),
                _and(other.where_criterion, other.having_criterion),
            )
            return QueryModifier(
                joins=self.joins + other.joins, having_criterion=result_having_criterion
            )

        if self.where_criterion and other.where_criterion:
            return QueryModifier(
                where_criterion=self.where_criterion | other.where_criterion,
                joins=self.joins + other.joins,
            )

        return QueryModifier(
            where_criterion=self.where_criterion or other.where_criterion,
            joins=self.joins + other.joins,
        )

    def __invert__(self) -> "QueryModifier":
        if not self.where_criterion and not self.having_criterion:
            return QueryModifier(joins=self.joins)
        if self.having_criterion:
            # TODO: This could be optimized?
            return QueryModifier(
                joins=self.joins,
                having_criterion=_and(self.where_criterion, self.having_criterion).negate(),
            )
        return QueryModifier(where_criterion=self.where_criterion.negate(), joins=self.joins)

    def get_query_modifiers(self) -> Tuple[Criterion, List[Tuple[Table, Criterion]], Criterion]:
        """
        Returns a tuple of the query criterion.
        """
        return self.where_criterion, self.joins, self.having_criterion


class Q:
    """
    Q Expression container.
    Q Expressions are a useful tool to compose a query from many small parts.

    :param join_type: Is the join an AND or OR join type?
    :param args: Inner ``Q`` expressions that you want to wrap.
    :param kwargs: Filter statements that this Q object should encapsulate.
    """

    __slots__ = (
        "children",
        "filters",
        "join_type",
        "_is_negated",
        "_annotations",
        "_custom_filters",
    )

    AND = "AND"
    OR = "OR"

    def __init__(self, *args: "Q", join_type: str = AND, **kwargs: Any) -> None:
        if args and kwargs:
            newarg = Q(join_type=join_type, **kwargs)
            args = (newarg,) + args
            kwargs = {}
        if not all(isinstance(node, Q) for node in args):
            raise OperationalError("All ordered arguments must be Q nodes")
        #: Contains the sub-Q's that this Q is made up of
        self.children: Tuple[Q, ...] = args
        #: Contains the filters applied to this Q
        self.filters: Dict[str, Any] = kwargs
        if join_type not in {self.AND, self.OR}:
            raise OperationalError("join_type must be AND or OR")
        #: Specifies if this Q does an AND or OR on its children
        self.join_type = join_type
        self._is_negated = False
        self._annotations: Dict[str, Any] = {}
        self._custom_filters: Dict[str, Dict[str, Any]] = {}

    def __and__(self, other: "Q") -> "Q":
        """
        Returns a binary AND of Q objects, use ``AND`` operator.

        :raises OperationalError: AND operation requires a Q node
        """
        if not isinstance(other, Q):
            raise OperationalError("AND operation requires a Q node")
        return Q(self, other, join_type=self.AND)

    def __or__(self, other: "Q") -> "Q":
        """
        Returns a binary OR of Q objects, use ``OR`` operator.

        :raises OperationalError: OR operation requires a Q node
        """
        if not isinstance(other, Q):
            raise OperationalError("OR operation requires a Q node")
        return Q(self, other, join_type=self.OR)

    def __invert__(self) -> "Q":
        """
        Returns a negated instance of the Q object, use ``~`` operator.
        """
        q = Q(*self.children, join_type=self.join_type, **self.filters)
        q.negate()
        return q

    def negate(self) -> None:
        """
        Negates the curent Q object. (mutation)
        """
        self._is_negated = not self._is_negated

    def _resolve_nested_filter(
        self, model: "Type[Model]", key: str, value: Any, table: Table
    ) -> QueryModifier:
        related_field_name = key.split("__")[0]
        related_field = cast(RelationalField, model._meta.fields_map[related_field_name])
        required_joins = _get_joins_for_related_field(table, related_field, related_field_name)
        modifier = Q(**{"__".join(key.split("__")[1:]): value}).resolve(
            model=related_field.related_model,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
            table=required_joins[-1][0],
        )

        return QueryModifier(joins=required_joins) & modifier

    def _resolve_custom_kwarg(
        self, model: "Type[Model]", key: str, value: Any, table: Table
    ) -> QueryModifier:
        having_info = self._custom_filters[key]
        annotation = self._annotations[having_info["field"]]
        annotation_info = annotation.resolve(model, table)
        operator = having_info["operator"]
        overridden_operator = model._meta.db.executor_class.get_overridden_filter_func(
            filter_func=operator
        )
        if overridden_operator:
            operator = overridden_operator
        if annotation_info["field"].is_aggregate:
            modifier = QueryModifier(having_criterion=operator(annotation_info["field"], value))
        else:
            modifier = QueryModifier(where_criterion=operator(annotation_info["field"], value))
        return modifier

    def _resolve_regular_kwarg(
        self, model: "Type[Model]", key: str, value: Any, table: Table
    ) -> QueryModifier:
        if key not in model._meta.filters and key.split("__")[0] in model._meta.fetch_fields:
            modifier = self._resolve_nested_filter(model, key, value, table)
        else:
            criterion, join = _process_filter_kwarg(model, key, value, table)
            joins = [join] if join else []
            modifier = QueryModifier(where_criterion=criterion, joins=joins)
        return modifier

    def _get_actual_filter_params(
        self, model: "Type[Model]", key: str, value: Table
    ) -> Tuple[str, Any]:
        filter_key = key
        if key in model._meta.fk_fields or key in model._meta.o2o_fields:
            field_object = model._meta.fields_map[key]
            if hasattr(value, "pk"):
                filter_value = value.pk
            else:
                filter_value = value
            filter_key = cast(str, field_object.source_field)
        elif key in model._meta.m2m_fields:
            if hasattr(value, "pk"):
                filter_value = value.pk
            else:
                filter_value = value
        elif (
            key.split("__")[0] in model._meta.fetch_fields
            or key in self._custom_filters
            or key in model._meta.filters
        ):
            filter_value = value
        else:
            allowed = sorted(
                model._meta.fields | model._meta.fetch_fields | set(self._custom_filters)
            )
            raise FieldError(f"Unknown filter param '{key}'. Allowed base values are {allowed}")
        return filter_key, filter_value

    def _resolve_kwargs(self, model: "Type[Model]", table: Table) -> QueryModifier:
        modifier = QueryModifier()
        for raw_key, raw_value in self.filters.items():
            key, value = self._get_actual_filter_params(model, raw_key, raw_value)
            if key in self._custom_filters:
                filter_modifier = self._resolve_custom_kwarg(model, key, value, table)
            else:
                filter_modifier = self._resolve_regular_kwarg(model, key, value, table)

            if self.join_type == self.AND:
                modifier &= filter_modifier
            else:
                modifier |= filter_modifier
        if self._is_negated:
            modifier = ~modifier
        return modifier

    def _resolve_children(self, model: "Type[Model]", table: Table) -> QueryModifier:
        modifier = QueryModifier()
        for node in self.children:
            node_modifier = node.resolve(model, self._annotations, self._custom_filters, table)
            if self.join_type == self.AND:
                modifier &= node_modifier
            else:
                modifier |= node_modifier

        if self._is_negated:
            modifier = ~modifier
        return modifier

    def resolve(
        self,
        model: "Type[Model]",
        annotations: Dict[str, Any],
        custom_filters: Dict[str, Dict[str, Any]],
        table: Table,
    ) -> QueryModifier:
        """
        Resolves the logical Q chain into the parts of a SQL statement.

        :param model: The Model this Q Expression should be resolved on.
        :param annotations: Extra annotations one wants to inject into the resultset.
        :param custom_filters: Pre-resolved filters to be passed though.
        :param table: ``pypika.Table`` to keep track of the virtual SQL table
            (to allow self referential joins)
        """
        self._annotations = annotations
        self._custom_filters = custom_filters
        if self.filters:
            return self._resolve_kwargs(model, table)
        return self._resolve_children(model, table)


class Prefetch:
    """
    Prefetcher container. One would directly use this when wanting to attach a custom QuerySet
    for specialised prefetching.

    :param relation: Related field name.
    :param queryset: Custom QuerySet to use for prefetching.
    """

    __slots__ = ("relation", "queryset")

    def __init__(self, relation: str, queryset: "QuerySet") -> None:
        self.relation = relation
        self.queryset = queryset
        self.queryset.query = copy(self.queryset.model._meta.basequery)

    def resolve_for_queryset(self, queryset: "QuerySet") -> None:
        """
        Called internally to generate prefetching query.

        :param queryset: Custom QuerySet to use for prefetching.
        :raises OperationalError: If field does not exist in model.
        """
        relation_split = self.relation.split("__")
        first_level_field = relation_split[0]
        if first_level_field not in queryset.model._meta.fetch_fields:
            raise OperationalError(
                f"relation {first_level_field} for {queryset.model._meta.db_table} not found"
            )
        forwarded_prefetch = "__".join(relation_split[1:])
        if forwarded_prefetch:
            if first_level_field not in queryset._prefetch_map.keys():
                queryset._prefetch_map[first_level_field] = set()
            queryset._prefetch_map[first_level_field].add(
                Prefetch(forwarded_prefetch, self.queryset)
            )
        else:
            queryset._prefetch_queries[first_level_field] = self.queryset
