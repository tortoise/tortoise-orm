from __future__ import annotations

from pypika_tortoise.terms import Function


class Rand(Function):
    """
    Generate random number, with optional seed.

    :samp:`Rand()`
    """

    def __init__(self, seed: int | None = None, alias=None) -> None:
        super().__init__("RAND", seed, alias=alias)
        self.args = [self.wrap_constant(seed)] if seed is not None else []
