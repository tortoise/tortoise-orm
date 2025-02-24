from __future__ import annotations

from typing import Any

from tortoise.fields import Field


class TSVectorField(Field):
    SQL_TYPE = "TSVECTOR"


class ArrayField(Field, list):  # type: ignore
    def __init__(self, element_type: str = "int", **kwargs: Any):
        super().__init__(**kwargs)
        self.element_type = element_type.upper()

    @property
    def SQL_TYPE(self) -> str:  # type: ignore
        return f"{self.element_type}[]"
