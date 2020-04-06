from typing import TYPE_CHECKING, Any, Optional, Type, Union, cast

from pypika import Table, functions
from pypika.functions import DistinctOptionFunction
from pypika.terms import ArithmeticExpression
from pypika.terms import Function as BaseFunction

from tortoise.exceptions import ConfigurationError
from tortoise.expressions import F
from tortoise.fields.relational import BackwardFKRelation, ForeignKeyFieldInstance, RelationalField

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model
    from tortoise.fields.base import Field


##############################################################################
# Base
##############################################################################


class Function:
    """
    Function/Aggregate base.

    :param field: Field name
    :param default_values: Extra parameters to the function.

    .. attribute:: database_func
        :annotation: pypika.terms.Function

        The pypika function this represents.

    .. attribute:: populate_field_object
        :annotation: bool = False

        Enable populate_field_object where we want to try and preserve the field type.
    """

    __slots__ = ("field", "field_object", "default_values")

    database_func = BaseFunction
    # Enable populate_field_object where we want to try and preserve the field type.
    populate_field_object = False

    def __init__(self, field: Union[str, F, ArithmeticExpression], *default_values: Any) -> None:
        self.field = field
        self.field_object: "Optional[Field]" = None
        self.default_values = default_values

    def _get_function_field(
        self, field: "Union[ArithmeticExpression, Field, str]", *default_values
    ):
        return self.database_func(field, *default_values)

    def _resolve_field_for_model(
        self, model: "Type[Model]", table: Table, field: str, *default_values: Any
    ) -> dict:
        joins = []
        fields = field.split("__")

        for iter_field in fields[:-1]:
            if iter_field not in model._meta.fetch_fields:
                raise ConfigurationError(f"{field} not resolvable")

            related_field = cast(RelationalField, model._meta.fields_map[iter_field])
            joins.append((table, iter_field, related_field))

            model = related_field.related_model
            related_table: Table = related_field.related_model._meta.basetable
            if isinstance(related_field, ForeignKeyFieldInstance):
                # Only FK's can be to same table, so we only auto-alias FK join tables
                related_table = related_table.as_(f"{table.get_table_name()}__{iter_field}")
            table = related_table

        last_field = fields[-1]
        if last_field in model._meta.fetch_fields:
            related_field = cast(RelationalField, model._meta.fields_map[last_field])
            related_field_meta = related_field.related_model._meta
            joins.append((table, last_field, related_field))
            related_table = related_field_meta.basetable

            if isinstance(related_field, BackwardFKRelation):
                if table == related_table:
                    related_table = related_table.as_(f"{table.get_table_name()}__{last_field}")

            field = related_table[related_field_meta.db_pk_column]
        else:
            field_object = model._meta.fields_map[last_field]
            if field_object.source_field:
                field = table[field_object.source_field]
            else:
                field = table[last_field]
            if self.populate_field_object:
                self.field_object = model._meta.fields_map.get(last_field, None)
                if self.field_object:  # pragma: nobranch
                    func = self.field_object.get_for_dialect(
                        model._meta.db.capabilities.dialect, "function_cast"
                    )
                    if func:
                        field = func(self.field_object, field)

        return {"joins": joins, "field": self._get_function_field(field, *default_values)}

    def resolve(self, model: "Type[Model]", table: Table) -> dict:
        """
        Used to resolve the Function statement for SQL generation.

        :param model: Model the function is applied on to.
        :param table: ``pypika.Table`` to keep track of the virtual SQL table
            (to allow self referential joins)
        :return: Dict with keys ``"joins"`` and ``"fields"``
        """

        if isinstance(self.field, str):
            function = self._resolve_field_for_model(model, table, self.field, *self.default_values)
            return function
        else:
            field, field_object = F.resolver_arithmetic_expression(model, self.field)
            if self.populate_field_object:
                self.field_object = field_object
            return {"joins": [], "field": self._get_function_field(field, *self.default_values)}


class Aggregate(Function):
    """
    Base for SQL Aggregates.

    :param field: Field name
    :param default_values: Extra parameters to the function.
    :param is_distinct: Flag for aggregate with distinction
    """

    database_func = DistinctOptionFunction

    def __init__(
        self, field: Union[str, F, ArithmeticExpression], *default_values: Any, distinct=False
    ) -> None:
        super().__init__(field, *default_values)
        self.distinct = distinct

    def _get_function_field(
        self, field: "Union[ArithmeticExpression, Field, str]", *default_values
    ):
        if self.distinct:
            return self.database_func(field, *default_values).distinct()
        else:
            return self.database_func(field, *default_values)


##############################################################################
# Standard functions
##############################################################################


class Trim(Function):
    """
    Trims whitespace off edges of text.

    :samp:`Trim("{FIELD_NAME}")`
    """

    database_func = functions.Trim


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
