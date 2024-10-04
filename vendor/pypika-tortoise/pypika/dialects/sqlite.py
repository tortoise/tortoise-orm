from typing import Any

from pypika.enums import Dialects
from pypika.queries import Query, QueryBuilder
from pypika.terms import ValueWrapper


class SQLLiteValueWrapper(ValueWrapper):
    def get_value_sql(self, **kwargs: Any) -> str:
        if isinstance(self.value, bool):
            return "1" if self.value else "0"
        return super().get_value_sql(**kwargs)


class SQLLiteQuery(Query):
    """
    Defines a query class for use with Microsoft SQL Server.
    """

    @classmethod
    def _builder(cls, **kwargs: Any) -> "SQLLiteQueryBuilder":
        return SQLLiteQueryBuilder(**kwargs)


class SQLLiteQueryBuilder(QueryBuilder):
    QUERY_CLS = SQLLiteQuery

    def __init__(self, **kwargs):
        super(SQLLiteQueryBuilder, self).__init__(
            dialect=Dialects.SQLITE, wrapper_cls=SQLLiteValueWrapper, **kwargs
        )

    def get_sql(self, **kwargs: Any) -> str:
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
            querystring = super(SQLLiteQueryBuilder, self).get_sql(**kwargs)
        return querystring
