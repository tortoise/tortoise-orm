from tortoise.queryset import QuerySet


class Manager:
    def __init__(self):
        self._model = None

    def get_queryset(self):
        return QuerySet(self._model)

    def __getattr__(self, item):
        return getattr(self.get_queryset(), item)
