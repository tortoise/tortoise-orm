import typing
from collections.abc import Callable
from typing import Any, Optional, Type

if typing.TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


def get_annotations(cls: "Type[Model]", method: Optional[Callable] = None) -> dict[str, Any]:
    """
    Get all annotations including base classes
    :param cls: The model class we need annotations from
    :param method: If specified, we try to get the annotations for the callable
    :return: The list of annotations
    """
    return typing.get_type_hints(method or cls)
