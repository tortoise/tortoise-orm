import datetime
import sqlite3
from decimal import Decimal
from typing import Any

from pypika_tortoise.queries import QueryBuilder

from tortoise import Model
from tortoise.backends.base.executor import BaseExecutor
from tortoise.contrib.sqlite.regex import (
    insensitive_posix_sqlite_regexp,
    posix_sqlite_regexp,
)
from tortoise.fields import BigIntField, IntField, SmallIntField
from tortoise.filters import insensitive_posix_regex, posix_regex

# Conversion for the cases where it's hard to know the
# related field, e.g. in raw queries, math or annotations.
sqlite3.register_adapter(Decimal, str)
sqlite3.register_adapter(datetime.date, lambda val: val.isoformat())
sqlite3.register_adapter(datetime.datetime, lambda val: val.isoformat(" "))


class SqliteExecutor(BaseExecutor):
    EXPLAIN_PREFIX = "EXPLAIN QUERY PLAN"
    DB_NATIVE = {bytes, str, int, float}
    FILTER_FUNC_OVERRIDE = {
        posix_regex: posix_sqlite_regexp,
        insensitive_posix_regex: insensitive_posix_sqlite_regexp,
    }

    def _add_returning_to_insert(
        self,
        query: QueryBuilder,
        has_generated: bool,
        db_default_columns: list[str],
    ) -> QueryBuilder:
        returning_fields = self._get_returning_fields(has_generated, db_default_columns)
        if returning_fields:
            query = query.returning(*returning_fields)  # type: ignore[operator]
        return query

    async def _execute_insert_dynamic(
        self,
        instance: Model,
        columns: list[str],
        has_generated: bool,
    ) -> Any:
        """Execute dynamic INSERT with RETURNING via execute_query.

        SQLite's ``execute_insert`` only returns ``lastrowid``.
        When we have a RETURNING clause, we use ``execute_query`` instead,
        which returns ``(count, rows)``.  We return ``dict(rows[0])`` so
        that ``_process_insert_result`` receives a dict (the RETURNING path).
        """
        query, values, db_default_columns = self._build_insert_with_defaults(
            instance, columns=columns, has_generated=has_generated
        )
        if db_default_columns:
            _, rows = await self.db.execute_query(query, values)
            if rows:
                return dict(rows[0])
            return None
        return await self.db.execute_insert(query, values)

    async def _process_insert_result(self, instance: Model, results: Any) -> None:
        if isinstance(results, int):
            pk_field_object = self.model._meta.pk
            if (
                isinstance(pk_field_object, (SmallIntField, IntField, BigIntField))
                and pk_field_object.generated
            ):
                instance.pk = results
        elif isinstance(results, dict):
            db_projection = instance._meta.fields_db_projection_reverse
            for key, val in results.items():
                if key in db_projection:
                    model_field = db_projection[key]
                    field_object = self.model._meta.fields_map[model_field]
                    setattr(instance, model_field, field_object.to_python_value(val))

        # SQLite can only generate a single ROWID
        #   so if any other primary key, it won't generate what we want.
