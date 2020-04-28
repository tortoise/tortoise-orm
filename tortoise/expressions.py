from typing import TYPE_CHECKING, Optional, Tuple, Type

from pypika import Field
from pypika.terms import ArithmeticExpression, Term

from tortoise.exceptions import FieldError

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


class F(Field):  # type: ignore
    @classmethod
    def resolver_arithmetic_expression(
        cls, model: "Type[Model]", arithmetic_expression_or_field: Term,
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
