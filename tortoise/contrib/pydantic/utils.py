import typing
from typing import Any, Callable, Dict, Optional, Type

if typing.TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


def get_annotations(cls: "Type[Model]", method: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Get all annotations including base classes
    :param cls: The model class we need annotations from
    :param method: If specified, we try to get the annotations for the callable
    :return: The list of annotations
    """
    return typing.get_type_hints(method or cls)
