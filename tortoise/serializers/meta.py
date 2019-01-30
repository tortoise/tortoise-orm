from typing import Any, Set, Type  # noqa
from tortoise.models import Model  # noqa


class MetaInfo:

    def __init__(self, meta: Any):
        self.model = getattr(meta, 'model', None)  # type: Type[Model]
        self.fields = getattr(meta, 'fields', set())  # type: Set[str]
        self.exclude = getattr(meta, 'exclude', set())  # type: Set[str]
        self.options = getattr(meta, 'options', {})  # type: dict
