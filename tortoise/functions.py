from typing import Any

from pypika import functions
from pypika.terms import AggregateFunction
from pypika.terms import Function as BaseFunction

from tortoise.exceptions import ConfigurationError

##############################################################################
# Base
##############################################################################


class Function:
    __slots__ = ("field", "field_object", "default_values")

    database_func = BaseFunction
    #: Enable populate_field_object where we want to try and preserve the field type.
    populate_field_object = False

    def __init__(self, field, *default_values) -> None:
        self.field = field
        self.field_object: Any = None
        self.default_values = default_values

    def _resolve_field_for_model(self, model, field: str, *default_values) -> dict:
        field_split = field.split("__")
        if not field_split[1:]:
            function_joins = []
            if field_split[0] in model._meta.fetch_fields:
                related_field = model._meta.fields_map[field_split[0]]
                related_field_meta = related_field.model_class._meta
                join = (model._meta.basetable, field_split[0], related_field)
                function_joins.append(join)
                field = related_field_meta.basetable[related_field_meta.db_pk_field]
            else:
                field = model._meta.basetable[field_split[0]]

                if self.populate_field_object:
                    self.field_object = model._meta.fields_map.get(field_split[0], None)
                    if self.field_object:  # pragma: nobranch
                        func = self.field_object.get_for_dialect(
                            model._meta.db.capabilities.dialect, "function_cast"
                        )
                        if func:
                            field = func(self.field_object, field)

            function_field = self.database_func(field, *default_values)
            return {"joins": function_joins, "field": function_field}

        if field_split[0] not in model._meta.fetch_fields:
            raise ConfigurationError(f"{field} not resolvable")
        related_field = model._meta.fields_map[field_split[0]]
        join = (model._meta.basetable, field_split[0], related_field)
        function = self._resolve_field_for_model(
            related_field.model_class, "__".join(field_split[1:]), *default_values
        )
        function["joins"].append(join)
        return function

    def resolve(self, model) -> dict:
        function = self._resolve_field_for_model(model, self.field, *self.default_values)
        function["joins"] = reversed(function["joins"])
        return function


class Aggregate(Function):
    database_func = AggregateFunction


##############################################################################
# Standard functions
##############################################################################


class Trim(Function):
    database_func = functions.Trim


class Length(Function):
    database_func = functions.Length


class Coalesce(Function):
    database_func = functions.Coalesce


class Lower(Function):
    database_func = functions.Lower


class Upper(Function):
    database_func = functions.Upper


##############################################################################
# Aggregate functions
##############################################################################


class Count(Aggregate):
    database_func = functions.Count


class Sum(Aggregate):
    database_func = functions.Sum
    populate_field_object = True


class Max(Aggregate):
    database_func = functions.Max
    populate_field_object = True


class Min(Aggregate):
    database_func = functions.Min
    populate_field_object = True


class Avg(Aggregate):
    database_func = functions.Avg
    populate_field_object = True
