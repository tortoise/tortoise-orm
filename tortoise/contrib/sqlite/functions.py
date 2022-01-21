from pypika.terms import Function


class Random(Function):  # type: ignore
    """
    Genrate random number.

    :samp:`Random()`
    """

    def __init__(self, alias=None) -> None:
        super().__init__("RANDOM", alias=alias)
