import itertools
from copy import copy
from typing import Any, Union

from pypika.enums import Dialects
from pypika.queries import Query, QueryBuilder
from pypika.terms import ArithmeticExpression, Field, Function, Star, Term
from pypika.utils import QueryException, builder


class PostgreSQLQuery(Query):
    """
    Defines a query class for use with PostgreSQL.
    """

    @classmethod
    def _builder(cls, **kwargs) -> "PostgreSQLQueryBuilder":
        return PostgreSQLQueryBuilder(**kwargs)


class PostgreSQLQueryBuilder(QueryBuilder):
    ALIAS_QUOTE_CHAR = '"'
    QUERY_CLS = PostgreSQLQuery

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(dialect=Dialects.POSTGRESQL, **kwargs)
        self._returns = []
        self._return_star = False

        self._distinct_on = []

    def __copy__(self) -> "PostgreSQLQueryBuilder":
        newone = super().__copy__()
        newone._returns = copy(self._returns)
        newone._on_conflict_do_updates = copy(self._on_conflict_do_updates)
        return newone

    @builder
    def distinct_on(self, *fields: Union[str, Term]) -> "PostgreSQLQueryBuilder":
        for field in fields:
            if isinstance(field, str):
                self._distinct_on.append(Field(field))
            elif isinstance(field, Term):
                self._distinct_on.append(field)

    def _distinct_sql(self, **kwargs: Any) -> str:
        if self._distinct_on:
            return "DISTINCT ON({distinct_on}) ".format(
                distinct_on=",".join(
                    term.get_sql(with_alias=True, **kwargs) for term in self._distinct_on
                )
            )
        return super()._distinct_sql(**kwargs)

    @builder
    def returning(self, *terms: Any) -> "PostgreSQLQueryBuilder":
        for term in terms:
            if isinstance(term, Field):
                self._return_field(term)
            elif isinstance(term, str):
                self._return_field_str(term)
            elif isinstance(term, ArithmeticExpression):
                self._return_other(term)
            elif isinstance(term, Function):
                raise QueryException("Aggregate functions are not allowed in returning")
            else:
                self._return_other(self.wrap_constant(term, self._wrapper_cls))

    def _validate_returning_term(self, term: Term) -> None:
        for field in term.fields_():
            if not any([self._insert_table, self._update_table, self._delete_from]):
                raise QueryException("Returning can't be used in this query")

            table_is_insert_or_update_table = field.table in {
                self._insert_table,
                self._update_table,
            }
            join_tables = set(
                itertools.chain.from_iterable([j.criterion.tables_ for j in self._joins])
            )
            join_and_base_tables = set(self._from) | join_tables
            table_not_base_or_join = bool(term.tables_ - join_and_base_tables)
            if not table_is_insert_or_update_table and table_not_base_or_join:
                raise QueryException("You can't return from other tables")

    def _set_returns_for_star(self) -> None:
        self._returns = [
            returning for returning in self._returns if not hasattr(returning, "table")
        ]
        self._return_star = True

    def _return_field(self, term: Union[str, Field]) -> None:
        if self._return_star:
            # Do not add select terms after a star is selected
            return

        self._validate_returning_term(term)

        if isinstance(term, Star):
            self._set_returns_for_star()

        self._returns.append(term)

    def _return_field_str(self, term: Union[str, Field]) -> None:
        if term == "*":
            self._set_returns_for_star()
            self._returns.append(Star())
            return

        if self._insert_table:
            self._return_field(Field(term, table=self._insert_table))
        elif self._update_table:
            self._return_field(Field(term, table=self._update_table))
        elif self._delete_from:
            self._return_field(Field(term, table=self._from[0]))
        else:
            raise QueryException("Returning can't be used in this query")

    def _return_other(self, function: Term) -> None:
        self._validate_returning_term(function)
        self._returns.append(function)

    def _returning_sql(self, **kwargs: Any) -> str:
        return " RETURNING {returning}".format(
            returning=",".join(term.get_sql(with_alias=True, **kwargs) for term in self._returns),
        )

    def get_sql(self, with_alias: bool = False, subquery: bool = False, **kwargs: Any) -> str:
        self._set_kwargs_defaults(kwargs)
        if not (self._selects or self._insert_table or self._delete_from or self._update_table):
            return ""
        if self._insert_table and not (self._selects or self._values):
            return ""
        if self._update_table and not self._updates:
            return ""

        has_joins = bool(self._joins)
        has_multiple_from_clauses = 1 < len(self._from)
        has_subquery_from_clause = 0 < len(self._from) and isinstance(self._from[0], QueryBuilder)
        has_reference_to_foreign_table = self._foreign_table
        has_update_from = self._update_table and self._from

        kwargs["with_namespace"] = any(
            [
                has_joins,
                has_multiple_from_clauses,
                has_subquery_from_clause,
                has_reference_to_foreign_table,
                has_update_from,
            ]
        )
        if self._update_table:
            if self._with:
                querystring = self._with_sql(**kwargs)
            else:
                querystring = ""

            querystring += self._update_sql(**kwargs)

            querystring += self._set_sql(**kwargs)

            if self._joins:
                self._from.append(self._update_table.as_(self._update_table.get_table_name() + "_"))

            if self._from:
                querystring += self._from_sql(**kwargs)
            if self._joins:
                querystring += " " + " ".join(join.get_sql(**kwargs) for join in self._joins)

            if self._wheres:
                querystring += self._where_sql(**kwargs)

            if self._orderbys:
                querystring += self._orderby_sql(**kwargs)
            if self._limit:
                querystring += self._limit_sql()
        else:
            querystring = super(PostgreSQLQueryBuilder, self).get_sql(
                with_alias, subquery, **kwargs
            )
        if self._returns:
            kwargs["with_namespace"] = self._update_table and self.from_
            querystring += self._returning_sql(**kwargs)
        return querystring
