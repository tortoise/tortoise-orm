from typing import Any

from pypika_tortoise import SqlContext, functions
from pypika_tortoise.terms import Term

from tortoise.expressions import Aggregate, CombinedExpression, F, Function

##############################################################################
# Standard functions
##############################################################################


class Trim(Function):
    """
    Trims whitespace off edges of text.

    :samp:`Trim("{FIELD_NAME}")`
    """

    database_func = functions.Trim

    def __init__(
        self,
        field: str | F | CombinedExpression | Function | Term,
        trim_chars: str = " ",
        *default_values: Any,
    ) -> None:
        super().__init__(field, trim_chars, *default_values)

    database_func = functions.Trim


class LTrim(Function):
    """
    Trims whitespace from the left side of text.

    :samp:`LTrim("{FIELD_NAME}")`
    """

    database_func = functions.LTrim


class RTrim(Function):
    """
    Trims whitespace from the right side of text.

    :samp:`RTrim("{FIELD_NAME}")`
    """

    database_func = functions.RTrim


class Replace(Function):
    """
    Replaces all occurrences of a search string with a replacement string.

    :samp:`Replace("{FIELD_NAME}", "search", "replacement")`
    """

    def __init__(
        self,
        field: str | F | CombinedExpression | Function | Term,
        search: str,
        replacement: str,
        *default_values: Any,
    ) -> None:
        super().__init__(field, search, replacement, *default_values)

    database_func = functions.Replace


class Length(Function):
    """
    Returns length of text/blob.

    :samp:`Length("{FIELD_NAME}")`
    """

    database_func = functions.Length


class Coalesce(Function):
    """
    Provides a default value if field is null.

    :samp:`Coalesce("{FIELD_NAME}", {DEFAULT_VALUE})`
    """

    database_func = functions.Coalesce


class Lower(Function):
    """
    Converts text to lower case.

    :samp:`Lower("{FIELD_NAME}")`
    """

    database_func = functions.Lower


class Upper(Function):
    """
    Converts text to upper case.

    :samp:`Upper("{FIELD_NAME}")`
    """

    database_func = functions.Upper


class _Concat(functions.Concat):
    @staticmethod
    def get_arg_sql(arg, ctx: SqlContext):
        sql = arg.get_sql(ctx.copy(with_alias=False)) if hasattr(arg, "get_sql") else str(arg)
        # explicitly convert to text for postgres to avoid errors like
        # "could not determine data type of parameter $1"
        if ctx.dialect.value == "postgresql":
            return f"{sql}::text"
        return sql


class Concat(Function):
    """
    Concate field or constant text.
    Be care, DB like sqlite3 has no support for `CONCAT`.

     :samp:`Concat("{FIELD_NAME}", {ANOTHER_FIELD_NAMES or CONSTANT_TEXT}, *args)`
    """

    database_func = _Concat


##############################################################################
# Aggregate functions
##############################################################################


class Count(Aggregate):
    """
    Counts the no of entries for that column.

    :samp:`Count("{FIELD_NAME}")`
    """

    database_func = functions.Count


class Sum(Aggregate):
    """
    Adds up all the values for that column.

    :samp:`Sum("{FIELD_NAME}")`
    """

    database_func = functions.Sum
    populate_field_object = True


class Max(Aggregate):
    """
    Returns largest value in the column.

    :samp:`Max("{FIELD_NAME}")`
    """

    database_func = functions.Max
    populate_field_object = True


class Min(Aggregate):
    """
    Returns smallest value in the column.

    :samp:`Min("{FIELD_NAME}")`
    """

    database_func = functions.Min
    populate_field_object = True


class Avg(Aggregate):
    """
    Returns average (mean) of all values in the column.

    :samp:`Avg("{FIELD_NAME}")`
    """

    database_func = functions.Avg
    populate_field_object = True
