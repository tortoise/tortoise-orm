from typing import Type

from tortoise.queryset import MODEL, QuerySet


class Manager:
    def __init__(self) -> None:
        self._model: Type[MODEL] = None  # type:ignore

    def get_queryset(self) -> QuerySet:
        return QuerySet(self._model)

    def __getattr__(self, item):
        return getattr(self.get_queryset(), item)
