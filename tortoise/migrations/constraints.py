from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UniqueConstraint:
    fields: tuple[str, ...]
    name: str | None = None
    condition: str | None = None

    def deconstruct(self) -> tuple[str, list, dict]:
        path = f"{self.__class__.__module__}.{self.__class__.__name__}"
        kwargs: dict = {"fields": self.fields, "name": self.name}
        if self.condition is not None:
            kwargs["condition"] = self.condition
        return path, [], kwargs


@dataclass(frozen=True)
class CheckConstraint:
    check: str
    name: str

    def deconstruct(self) -> tuple[str, list, dict]:
        path = f"{self.__class__.__module__}.{self.__class__.__name__}"
        return path, [], {"check": self.check, "name": self.name}
