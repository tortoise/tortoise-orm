from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UniqueConstraint:
    fields: tuple[str, ...]
    name: str | None = None

    def deconstruct(self) -> tuple[str, list, dict]:
        path = f"{self.__class__.__module__}.{self.__class__.__name__}"
        return path, [], {"fields": self.fields, "name": self.name}
