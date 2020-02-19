from typing import Union

from pypika import Field
from pypika.terms import ArithmeticExpression

from tortoise.exceptions import FieldError


class F(Field):  # type: ignore
    @classmethod
    def resolver_arithmetic_expression(
        cls,
        fields_db_projection: dict,
        arithmetic_expression_or_field: Union[ArithmeticExpression, Field],
    ):
        if isinstance(arithmetic_expression_or_field, Field):
            name = arithmetic_expression_or_field.name
            try:
                name = fields_db_projection[name]
            except KeyError:
                raise FieldError(f"Field {name} is virtual and can not be updated")
            arithmetic_expression_or_field.name = name
        elif isinstance(arithmetic_expression_or_field, ArithmeticExpression):
            left = arithmetic_expression_or_field.left
            right = arithmetic_expression_or_field.right
            arithmetic_expression_or_field.left = cls.resolver_arithmetic_expression(
                fields_db_projection, left
            )
            arithmetic_expression_or_field.right = cls.resolver_arithmetic_expression(
                fields_db_projection, right
            )
        return arithmetic_expression_or_field
