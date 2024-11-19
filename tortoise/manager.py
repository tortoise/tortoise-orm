from typing import Any

from tortoise.queryset import QuerySet


class Manager:
    """
    A Manager is the interface through which database query operations are provided to tortoise models.

    There is one default Manager for every tortoise model.
    """

    def __init__(self, model=None) -> None:
        self._model = model

    def get_queryset(self) -> QuerySet:
        return QuerySet(self._model)

    def __getattr__(self, item: str) -> Any:
        return getattr(self.get_queryset(), item)
