from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING, Any, Union, cast, get_args, get_origin

import pydantic
from pydantic import BaseModel, ConfigDict, RootModel

if sys.version_info >= (3, 11):  # pragma: nocoverage
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model
    from tortoise.queryset import QuerySet, QuerySetSingle


def _get_fetch_fields(pydantic_class: type[PydanticModel], model_class: type[Model]) -> list[str]:
    """
    Recursively collect fields needed to fetch
    :param pydantic_class: The pydantic model class
    :param model_class: The tortoise model class
    :return: The list of fields to be fetched
    """
    fetch_fields = []
    for field_name, field_type in pydantic_class.__annotations__.items():
        field_type = cast(Any, field_type)
        origin = cast(Any, get_origin(field_type))
        if origin is list:
            args = get_args(field_type)
            if args:
                field_type = args[0]
        elif origin is Union or origin is types.UnionType:
            args = get_args(field_type)
            for arg in args:
                if arg is not type(None):
                    field_type = arg
                    break

        if not isinstance(field_type, type):
            continue
        if field_name in model_class._meta.fetch_fields and issubclass(field_type, PydanticModel):
            subclass = field_type
            orig_model = cast(Any, subclass.model_config).get("orig_model")
            subclass_fetch_fields = _get_fetch_fields(subclass, orig_model)
            if subclass_fetch_fields:
                fetch_fields.extend([field_name + "__" + f for f in subclass_fetch_fields])
            else:
                fetch_fields.append(field_name)

    return fetch_fields


class PydanticModel(BaseModel):
    """
    Pydantic BaseModel for Tortoise objects.

    This provides an extra method above the usual Pydantic
    `model properties <https://docs.pydantic.dev/latest/usage/models/#model-properties>`__
    """

    model_config = ConfigDict(from_attributes=True)

    @pydantic.model_validator(mode="wrap")
    @classmethod
    def _tortoise_wrap(cls, values, handler):
        orm_obj = values if hasattr(values, "_meta") else None
        instance = handler(values)
        if orm_obj is not None:
            object.__setattr__(instance, "__orm_obj__", orm_obj)
        return instance

    @classmethod
    async def from_tortoise_orm(cls, obj: Model) -> Self:
        """
        Returns a serializable pydantic model instance built from the provided model instance.

        .. note::

            This will prefetch all the relations automatically. It is probably what you want.

            If you don't want this, or require a ``sync`` method, look to using ``.from_orm()``.

            In that case you'd have to manage  prefetching yourself,
            or exclude relational fields from being part of the model using
            :class:`tortoise.contrib.pydantic.creator.PydanticMeta`, or you would be
            getting ``OperationalError`` exceptions.

            This is due to how the ``asyncio`` framework forces I/O to happen in explicit ``await``
            statements. Hence we can only do lazy-fetching during an awaited method.

        :param obj: The Model instance you want serialized.
        """
        fetch_fields = _get_fetch_fields(cls, cls.model_config["orig_model"])  # type: ignore
        await obj.fetch_related(*fetch_fields)
        return cls.model_validate(obj)

    @classmethod
    async def from_queryset_single(cls, queryset: QuerySetSingle) -> Self:
        """
        Returns a serializable pydantic model instance for a single model
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticModel is based on.
        """
        fetch_fields = _get_fetch_fields(cls, cls.model_config["orig_model"])  # type: ignore
        return cls.model_validate(await queryset.prefetch_related(*fetch_fields))

    @classmethod
    async def from_queryset(cls, queryset: QuerySet) -> list[Self]:
        """
        Returns a serializable pydantic model instance that contains a list of models,
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticModel is based on.
        """
        fetch_fields = _get_fetch_fields(cls, cls.model_config["orig_model"])  # type: ignore
        return [cls.model_validate(e) for e in await queryset.prefetch_related(*fetch_fields)]


class PydanticListModel(RootModel):
    """
    Pydantic BaseModel for List of Tortoise Models

    This provides an extra method above the usual Pydantic
    `model properties <https://docs.pydantic.dev/latest/concepts/models/#model-methods-and-properties>`__
    """

    @classmethod
    async def from_queryset(cls, queryset: QuerySet) -> Self:
        """
        Returns a serializable pydantic model instance that contains a list of models,
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticListModel is based on.
        """
        submodel = cls.model_config["submodel"]  # type: ignore
        fetch_fields = _get_fetch_fields(submodel, submodel.model_config["orig_model"])
        return cls.model_validate(
            [submodel.model_validate(e) for e in await queryset.prefetch_related(*fetch_fields)]
        )
