from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, get_type_hints

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


def get_annotations(cls: type[Model], method: Callable | None = None) -> dict[str, Any]:
    """
    Get all annotations including base classes.

    Builds a namespace from the Tortoise apps registry so that forward references
    (string annotations) to models defined in other files can be resolved by
    :func:`typing.get_type_hints`.

    :param cls: The model class we need annotations from
    :param method: If specified, we try to get the annotations for the callable
    :return: The list of annotations
    """
    localns: dict[str, Any] = {}
    try:
        from tortoise import Tortoise

        if Tortoise.apps:
            for app_models in Tortoise.apps.values():
                localns.update(app_models)
    except Exception:  # nosec B110
        pass
    try:
        return get_type_hints(method or cls, localns=localns)
    except Exception:
        return getattr(method or cls, "__annotations__", {})
