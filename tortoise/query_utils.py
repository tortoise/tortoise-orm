from typing import Any, List, Mapping, Optional, Tuple  # noqa

from pypika import Table
from pypika.terms import Criterion

from tortoise import fields
from tortoise.exceptions import FieldError, OperationalError


def _process_filter_kwarg(model, key, value) -> Tuple[Criterion, Optional[Tuple[Table, Criterion]]]:
    join = None
    table = Table(model._meta.table)

    if value is None and "{}__isnull".format(key) in model._meta.filters:
        param = model._meta.get_filter("{}__isnull".format(key))
        value = True
    else:
        param = model._meta.get_filter(key)

    pk_db_field = model._meta.db_pk_field
    if param.get("table"):
        join = (
            param["table"],
            getattr(table, pk_db_field) == getattr(param["table"], param["backward_key"]),
        )
        if param.get("value_encoder"):
            value = param["value_encoder"](value, model)
        criterion = param["operator"](getattr(param["table"], param["field"]), value)
    else:
        field_object = model._meta.fields_map[param["field"]]
        encoded_value = (
            param["value_encoder"](value, model, field_object)
            if param.get("value_encoder")
            else model._meta.db.executor_class._field_to_db(field_object, value, model)
        )
        criterion = param["operator"](getattr(table, param["field"]), encoded_value)
    return criterion, join


def _get_joins_for_related_field(
    table, related_field, related_field_name
) -> List[Tuple[Table, Criterion]]:
    required_joins = []

    table_pk = related_field.model._meta.db_pk_field
    related_table_pk = related_field.type._meta.db_pk_field

    if isinstance(related_field, fields.ManyToManyField):
        related_table = Table(related_field.type._meta.table)
        through_table = Table(related_field.through)
        required_joins.append(
            (
                through_table,
                getattr(table, table_pk) == getattr(through_table, related_field.backward_key),
            )
        )
        required_joins.append(
            (
                related_table,
                getattr(through_table, related_field.forward_key)
                == getattr(related_table, related_table_pk),
            )
        )
    elif isinstance(related_field, fields.BackwardFKRelation):
        related_table = Table(related_field.type._meta.table)
        required_joins.append(
            (
                related_table,
                getattr(table, table_pk) == getattr(related_table, related_field.relation_field),
            )
        )
    else:
        related_table = Table(related_field.type._meta.table)
        required_joins.append(
            (
                related_table,
                getattr(related_table, related_table_pk)
                == getattr(table, "{}_id".format(related_field_name)),
            )
        )
    return required_joins


class EmptyCriterion:
    def __or__(self, other):
        if other:
            return other
        return self

    def __and__(self, other):
        if other:
            return other
        return self

    def __bool__(self):
        return False


def _and(left: Criterion, right: Criterion):
    if left and not right:
        return left
    return left & right


def _or(left: Criterion, right: Criterion):
    if left and not right:
        return left
    return left | right


class QueryModifier:
    def __init__(
        self,
        where_criterion: Optional[Criterion] = None,
        joins: Optional[List[Tuple[Criterion, Criterion]]] = None,
        having_criterion: Optional[Criterion] = None,
    ):
        self.where_criterion = where_criterion if where_criterion else EmptyCriterion()
        self.joins = joins if joins else []
        self.having_criterion = having_criterion if having_criterion else EmptyCriterion()

    def __and__(self, other: "QueryModifier") -> "QueryModifier":
        return QueryModifier(
            where_criterion=_and(self.where_criterion, other.where_criterion),
            joins=self.joins + other.joins,
            having_criterion=_and(self.having_criterion, other.having_criterion),
        )

    def __or__(self, other: "QueryModifier") -> "QueryModifier":
        if self.having_criterion or other.having_criterion:
            result_having_criterion = _or(
                _and(self.where_criterion, self.having_criterion),
                _and(other.where_criterion, other.having_criterion),
            )
            return QueryModifier(
                joins=self.joins + other.joins, having_criterion=result_having_criterion
            )
        return QueryModifier(
            where_criterion=self.where_criterion | other.where_criterion,
            joins=self.joins + other.joins,
        )

    def __invert__(self):
        if not self.where_criterion and not self.having_criterion:
            return QueryModifier(joins=self.joins)
        if self.having_criterion:
            return QueryModifier(
                joins=self.joins,
                having_criterion=_and(self.where_criterion, self.having_criterion).negate(),
            )
        return QueryModifier(where_criterion=self.where_criterion.negate(), joins=self.joins)

    def get_query_modifiers(self) -> Tuple[Criterion, List[Tuple[Table, Criterion]], Criterion]:
        return self.where_criterion, self.joins, self.having_criterion


class Q:  # pylint: disable=C0103
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

    def __init__(self, *args: "Q", join_type=AND, **kwargs) -> None:
        if args and kwargs:
            raise OperationalError("You can pass only Q nodes or filter kwargs in one Q node")
        if not all(isinstance(node, Q) for node in args):
            raise OperationalError("All ordered arguments must be Q nodes")
        self.children = args  # type: Tuple[Q, ...]
        self.filters = kwargs  # type: Mapping[str, Any]
        if join_type not in {self.AND, self.OR}:
            raise OperationalError("join_type must be AND or OR")
        self.join_type = join_type
        self._is_negated = False
        self._annotations = {}  # type: Mapping[str, Any]
        self._custom_filters = {}  # type: Mapping[str, Mapping[str, Any]]

    def __and__(self, other) -> "Q":
        if not isinstance(other, Q):
            raise OperationalError("AND operation requires a Q node")
        return Q(self, other, join_type=self.AND)

    def __or__(self, other) -> "Q":
        if not isinstance(other, Q):
            raise OperationalError("OR operation requires a Q node")
        return Q(self, other, join_type=self.OR)

    def __invert__(self) -> "Q":
        q = Q(*self.children, join_type=self.join_type, **self.filters)
        q.negate()
        return q

    def negate(self) -> None:
        self._is_negated = not self._is_negated

    def _resolve_nested_filter(self, model, key, value) -> QueryModifier:
        table = Table(model._meta.table)

        related_field_name = key.split("__")[0]
        related_field = model._meta.fields_map[related_field_name]
        required_joins = _get_joins_for_related_field(table, related_field, related_field_name)
        modifier = Q(**{"__".join(key.split("__")[1:]): value}).resolve(
            model=related_field.type,
            annotations=self._annotations,
            custom_filters=self._custom_filters,
        )

        return QueryModifier(joins=required_joins) & modifier

    def _resolve_custom_kwarg(self, model, key, value) -> QueryModifier:
        having_info = self._custom_filters[key]
        aggregation = self._annotations[having_info["field"]]
        aggregation_info = aggregation.resolve(model)
        operator = having_info["operator"]
        overridden_operator = model._meta.db.executor_class.get_overridden_filter_func(
            filter_func=operator
        )
        if overridden_operator:
            operator = overridden_operator
        return QueryModifier(having_criterion=operator(aggregation_info["field"], value))

    def _resolve_regular_kwarg(self, model, key, value) -> QueryModifier:
        if key not in model._meta.filters and key.split("__")[0] in model._meta.fetch_fields:
            modifier = self._resolve_nested_filter(model, key, value)
        else:
            criterion, join = _process_filter_kwarg(model, key, value)
            joins = [join] if join else []
            modifier = QueryModifier(where_criterion=criterion, joins=joins)
        return modifier

    def _get_actual_filter_params(self, model, key, value) -> Tuple[str, Any]:
        if key in model._meta.fk_fields:
            field_object = model._meta.fields_map[key]
            if hasattr(value, "pk"):
                filter_value = value.pk
            else:
                filter_value = value
            filter_key = field_object.source_field
        elif key in model._meta.m2m_fields:
            filter_key = key
            if hasattr(value, "pk"):
                filter_value = value.pk
            else:
                filter_value = value
        elif (
            key.split("__")[0] in model._meta.fetch_fields
            or key in self._custom_filters
            or key in model._meta.filters
        ):
            filter_key = key
            filter_value = value
        else:
            allowed = sorted(
                list(model._meta.fields | model._meta.fetch_fields | set(self._custom_filters))
            )
            raise FieldError(
                "Unknown filter param '{}'. Allowed base values are {}".format(key, allowed)
            )
        return filter_key, filter_value

    def _resolve_kwargs(self, model) -> QueryModifier:
        modifier = QueryModifier()
        for raw_key, raw_value in self.filters.items():
            key, value = self._get_actual_filter_params(model, raw_key, raw_value)
            if key in self._custom_filters:
                filter_modifier = self._resolve_custom_kwarg(model, key, value)
            else:
                filter_modifier = self._resolve_regular_kwarg(model, key, value)

            if self.join_type == self.AND:
                modifier &= filter_modifier
            else:
                modifier |= filter_modifier
        if self._is_negated:
            modifier = ~modifier
        return modifier

    def _resolve_children(self, model) -> QueryModifier:
        modifier = QueryModifier()
        for node in self.children:
            node_modifier = node.resolve(model, self._annotations, self._custom_filters)
            if self.join_type == self.AND:
                modifier &= node_modifier
            else:
                modifier |= node_modifier

        if self._is_negated:
            modifier = ~modifier
        return modifier

    def resolve(self, model, annotations, custom_filters) -> QueryModifier:
        self._annotations = annotations
        self._custom_filters = custom_filters
        if self.filters:
            return self._resolve_kwargs(model)
        else:
            return self._resolve_children(model)


class Prefetch:
    __slots__ = ("relation", "queryset")

    def __init__(self, relation, queryset) -> None:
        self.relation = relation
        self.queryset = queryset

    def resolve_for_queryset(self, queryset) -> None:
        relation_split = self.relation.split("__")
        first_level_field = relation_split[0]
        if first_level_field not in queryset.model._meta.fetch_fields:
            raise OperationalError(
                "relation {} for {} not found".format(first_level_field, queryset.model._meta.table)
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
