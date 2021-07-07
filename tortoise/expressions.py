from typing import TYPE_CHECKING, Any, Optional, Tuple, Type

from pypika import Field
from pypika.queries import Selectable
from pypika.terms import ArithmeticExpression, Term
from pypika.utils import format_alias_sql

from tortoise.exceptions import FieldError

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model
    from tortoise.queryset import AwaitableQuery


class F(Field):  # type: ignore
    @classmethod
    def resolver_arithmetic_expression(
        cls,
        model: "Type[Model]",
        arithmetic_expression_or_field: Term,
    ) -> Tuple[Term, Optional[Field]]:
        field_object = None

        if isinstance(arithmetic_expression_or_field, Field):
            name = arithmetic_expression_or_field.name
            try:
                arithmetic_expression_or_field.name = model._meta.fields_db_projection[name]

                field_object = model._meta.fields_map.get(name, None)
                if field_object:
                    func = field_object.get_for_dialect(
                        model._meta.db.capabilities.dialect, "function_cast"
                    )
                    if func:
                        arithmetic_expression_or_field = func(
                            field_object, arithmetic_expression_or_field
                        )
            except KeyError:
                raise FieldError(f"There is no non-virtual field {name} on Model {model.__name__}")
        elif isinstance(arithmetic_expression_or_field, ArithmeticExpression):
            left = arithmetic_expression_or_field.left
            right = arithmetic_expression_or_field.right
            (
                arithmetic_expression_or_field.left,
                left_field_object,
            ) = cls.resolver_arithmetic_expression(model, left)
            if left_field_object:
                if field_object and type(field_object) != type(left_field_object):
                    raise FieldError(
                        "Cannot use arithmetic expression between different field type"
                    )
                field_object = left_field_object

            (
                arithmetic_expression_or_field.right,
                right_field_object,
            ) = cls.resolver_arithmetic_expression(model, right)
            if right_field_object:
                if field_object and type(field_object) != type(right_field_object):
                    raise FieldError(
                        "Cannot use arithmetic expression between different field type"
                    )
                field_object = right_field_object

        return arithmetic_expression_or_field, field_object


class Subquery(Term):  # type: ignore
    def __init__(self, query: "AwaitableQuery"):
        super().__init__()
        self.query = query

    def get_sql(self, **kwargs: Any) -> str:
        return self.query.as_query().get_sql(**kwargs)

    def as_(self, alias: str) -> "Selectable":
        return self.query.as_query().as_(alias)


class RawSQL(Term):  # type: ignore
    def __init__(self, sql: str):
        super().__init__()
        self.sql = sql

    def get_sql(self, with_alias: bool = False, **kwargs: Any) -> str:
        if with_alias:
            return format_alias_sql(sql=self.sql, alias=self.alias, **kwargs)
        return self.sql
