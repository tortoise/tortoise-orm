from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional, get_type_hints

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


def get_annotations(cls: "type[Model]", method: Optional[Callable] = None, globalns: dict = None, localns: dict = None) -> dict[str, Any]:
    """
    Get all annotations including base classes
    :param cls: The model class we need annotations from
    :param method: If specified, we try to get the annotations for the callable
    :param globalns: If specified, use this dictionary as the globals map
    :param localns: If specified, use this dictionary as the locals map
    :return: The list of annotations
    """
    return get_type_hints(method or cls, globalns, localns)
