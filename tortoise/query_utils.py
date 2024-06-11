from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, List, Optional, Tuple

from pypika import Table
from pypika.terms import Criterion

from tortoise.exceptions import OperationalError
from tortoise.fields.relational import (
    BackwardFKRelation,
    ManyToManyFieldInstance,
    RelationalField,
)

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.queryset import QuerySet


TableCriterionTuple = Tuple[Table, Criterion]


def _get_joins_for_related_field(
    table: Table, related_field: RelationalField, related_field_name: str
) -> List[TableCriterionTuple]:
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
            (
                related_table,
                related_table[to_field_source_field] == table[from_field_source_field],
            )
        )
    return required_joins


class EmptyCriterion(Criterion):  # type:ignore[misc]
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
        joins: Optional[List[TableCriterionTuple]] = None,
        having_criterion: Optional[Criterion] = None,
    ) -> None:
        self.where_criterion: Criterion = where_criterion or EmptyCriterion()
        self.joins = joins or []
        self.having_criterion: Criterion = having_criterion or EmptyCriterion()

    def __and__(self, other: QueryModifier) -> QueryModifier:
        return self.__class__(
            where_criterion=_and(self.where_criterion, other.where_criterion),
            joins=self.joins + other.joins,
            having_criterion=_and(self.having_criterion, other.having_criterion),
        )

    def _and_criterion(self) -> Criterion:
        return _and(self.where_criterion, self.having_criterion)

    def __or__(self, other: QueryModifier) -> QueryModifier:
        where_criterion = having_criterion = None
        if self.having_criterion or other.having_criterion:
            having_criterion = _or(self._and_criterion(), other._and_criterion())
        else:
            where_criterion = (
                (self.where_criterion | other.where_criterion)
                if self.where_criterion and other.where_criterion
                else (self.where_criterion or other.where_criterion)
            )
        return self.__class__(where_criterion, self.joins + other.joins, having_criterion)

    def __invert__(self) -> QueryModifier:
        where_criterion = having_criterion = None
        if self.having_criterion:
            having_criterion = (self.where_criterion & self.having_criterion).negate()
        elif self.where_criterion:
            where_criterion = self.where_criterion.negate()
        return self.__class__(where_criterion, self.joins, having_criterion)

    def get_query_modifiers(self) -> Tuple[Criterion, List[TableCriterionTuple], Criterion]:
        """
        Returns a tuple of the query criterion.
        """
        return self.where_criterion, self.joins, self.having_criterion


class Prefetch:
    """
    Prefetcher container. One would directly use this when wanting to attach a custom QuerySet
    for specialised prefetching.

    :param relation: Related field name.
    :param queryset: Custom QuerySet to use for prefetching.
    :param to_attr: Sets the result of the prefetch operation to a custom attribute.
    """

    __slots__ = ("relation", "queryset", "to_attr")

    def __init__(self, relation: str, queryset: "QuerySet", to_attr: Optional[str] = None) -> None:
        self.to_attr = to_attr
        self.relation = relation
        self.queryset = queryset
        self.queryset.query = copy(self.queryset.model._meta.basequery)

    def resolve_for_queryset(self, queryset: "QuerySet") -> None:
        """
        Called internally to generate prefetching query.

        :param queryset: Custom QuerySet to use for prefetching.
        :raises OperationalError: If field does not exist in model.
        """

        first_level_field, __, forwarded_prefetch = self.relation.partition("__")
        if first_level_field not in queryset.model._meta.fetch_fields:
            raise OperationalError(
                f"relation {first_level_field} for {queryset.model._meta.db_table} not found"
            )

        if forwarded_prefetch:
            if first_level_field not in queryset._prefetch_map:
                queryset._prefetch_map[first_level_field] = set()
            queryset._prefetch_map[first_level_field].add(
                Prefetch(forwarded_prefetch, self.queryset, to_attr=self.to_attr)
            )
        else:
            queryset._prefetch_queries.setdefault(first_level_field, []).append(
                (self.to_attr, self.queryset)
            )
