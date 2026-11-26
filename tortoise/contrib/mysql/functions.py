from __future__ import annotations

from pypika_tortoise import functions
from pypika_tortoise.terms import Function, Term

from tortoise.expressions import CombinedExpression, F
from tortoise.functions import Function as TortoiseFunction


class Rand(Function):
    """
    Generate random number, with optional seed.

    :samp:`Rand()`
    """

    def __init__(self, seed: int | None = None, alias=None) -> None:
        super().__init__("RAND", seed, alias=alias)
        self.args = [self.wrap_constant(seed)] if seed is not None else []


class LPad(TortoiseFunction):
    """
    Pads the left side of a string with a specified character to reach a certain length.

    :samp:`LPad("{FIELD_NAME}", length, fill_text)`
    """

    def __init__(
        self,
        field: str | F | CombinedExpression | TortoiseFunction | Term,
        length: int,
        fill_text: str = " ",
    ) -> None:
        super().__init__(field, length, fill_text)

    database_func = functions.LPad


class RPad(TortoiseFunction):
    """
    Pads the right side of a string with a specified character to reach a certain length.

    :samp:`RPad("{FIELD_NAME}", length, fill_text)`
    """

    def __init__(
        self,
        field: str | F | CombinedExpression | TortoiseFunction | Term,
        length: int,
        fill_text: str = " ",
    ) -> None:
        super().__init__(field, length, fill_text)

    database_func = functions.RPad
