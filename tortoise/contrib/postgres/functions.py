from pypika_tortoise import functions
from pypika_tortoise.terms import Function, Term

from tortoise.expressions import CombinedExpression, F
from tortoise.functions import Function as TortoiseFunction


class ToTsVector(Function):
    """
    to to_tsvector function
    """

    def __init__(self, field: Term) -> None:
        super().__init__("TO_TSVECTOR", field)


class ToTsQuery(Function):
    """
    to_tsquery function
    """

    def __init__(self, field: Term) -> None:
        super().__init__("TO_TSQUERY", field)


class PlainToTsQuery(Function):
    """
    plainto_tsquery function
    """

    def __init__(self, field: Term) -> None:
        super().__init__("PLAINTO_TSQUERY", field)


class Random(Function):
    """
    Generate random number.

    :samp:`Random()`
    """

    def __init__(self, alias=None) -> None:
        super().__init__("RANDOM", alias=alias)


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
