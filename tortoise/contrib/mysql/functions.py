from typing import Union

from pypika.terms import Function, Parameter


class Rand(Function):  # type: ignore
    """
    Generate random number, with optional seed.

    :samp:`Rand()`
    """

    def __init__(self, seed: Union[int, None] = None, alias=None) -> None:
        super().__init__("RAND", seed, alias=alias)
        self.args = [self.wrap_constant(seed) if seed is not None else Parameter("")]
