import sys
from typing import TYPE_CHECKING, List, Type, Union

import pydantic
from pydantic import BaseModel, ConfigDict, RootModel

from tortoise import fields

if sys.version_info >= (3, 11):  # pragma: nocoverage
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model
    from tortoise.queryset import QuerySet, QuerySetSingle


def _get_fetch_fields(
    pydantic_class: "Type[PydanticModel]", model_class: "Type[Model]"
) -> list[str]:
    """
    Recursively collect fields needed to fetch
    :param pydantic_class: The pydantic model class
    :param model_class: The tortoise model class
    :return: The list of fields to be fetched
    """
    fetch_fields = []
    for field_name, field_type in pydantic_class.__annotations__.items():
        origin = getattr(field_type, "__origin__", None)
        if origin in (list, List, Union):
            field_type = field_type.__args__[0]

        # noinspection PyProtectedMember
        if field_name in model_class._meta.fetch_fields and issubclass(field_type, PydanticModel):
            subclass_fetch_fields = _get_fetch_fields(
                field_type, field_type.model_config["orig_model"]
            )
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

    # noinspection PyMethodParameters
    @pydantic.field_validator("*")  # It is a classmethod!
    def _tortoise_convert(cls, value):  # pylint: disable=E0213
        # Computed fields
        if callable(value):
            return value()
        # Convert ManyToManyRelation to list
        if isinstance(value, (fields.ManyToManyRelation, fields.ReverseRelation)):
            return list(value)
        return value

    @classmethod
    async def from_tortoise_orm(cls, obj: "Model") -> Self:
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
        # Get fields needed to fetch
        fetch_fields = _get_fetch_fields(cls, cls.model_config["orig_model"])  # type: ignore
        # Fetch fields
        await obj.fetch_related(*fetch_fields)
        return cls.model_validate(obj)

    @classmethod
    async def from_queryset_single(cls, queryset: "QuerySetSingle") -> Self:
        """
        Returns a serializable pydantic model instance for a single model
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticModel is based on.
        """
        fetch_fields = _get_fetch_fields(cls, cls.model_config["orig_model"])  # type: ignore
        return cls.model_validate(await queryset.prefetch_related(*fetch_fields))

    @classmethod
    async def from_queryset(cls, queryset: "QuerySet") -> list[Self]:
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
    async def from_queryset(cls, queryset: "QuerySet") -> Self:
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
