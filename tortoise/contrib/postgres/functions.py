from pypika.terms import Function, Term


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
