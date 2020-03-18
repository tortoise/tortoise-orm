from typing import TYPE_CHECKING, List, Type, Union

import pydantic
from pydantic import BaseModel  # pylint: disable=E0611

from tortoise import fields

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model
    from tortoise.queryset import QuerySet, QuerySetSingle


def _get_fetch_fields(
    pydantic_class: "Type[PydanticModel]", model_class: "Type[Model]"
) -> List[str]:
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
                field_type, getattr(field_type.__config__, "orig_model")
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
    `model properties <https://pydantic-docs.helpmanual.io/usage/models/#model-properties>`__
    """

    class Config:
        orm_mode = True  # It should be in ORM mode to convert tortoise data to pydantic

    # noinspection PyMethodParameters
    @pydantic.validator("*", pre=True, each_item=False)  # It is a classmethod!
    def _tortoise_convert(cls, value):  # pylint: disable=E0213
        # Computed fields
        if callable(value):
            return value()
        # Convert ManyToManyRelation to list
        elif isinstance(value, (fields.ManyToManyRelation, fields.ReverseRelation)):
            return list(value)
        return value

    @classmethod
    async def from_tortoise_orm(cls, obj: "Model") -> "PydanticModel":
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
        fetch_fields = _get_fetch_fields(cls, getattr(cls.__config__, "orig_model"))
        # Fetch fields
        await obj.fetch_related(*fetch_fields)
        # Convert to pydantic object
        values = super().from_orm(obj)
        return values

    @classmethod
    async def from_queryset_single(cls, queryset: "QuerySetSingle") -> "PydanticModel":
        """
        Returns a serializable pydantic model instance for a single model
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticModel is based on.
        """
        fetch_fields = _get_fetch_fields(cls, getattr(cls.__config__, "orig_model"))
        return cls.from_orm(await queryset.prefetch_related(*fetch_fields))

    @classmethod
    async def from_queryset(cls, queryset: "QuerySet") -> "List[PydanticModel]":
        """
        Returns a serializable pydantic model instance that contains a list of models,
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticModel is based on.
        """
        fetch_fields = _get_fetch_fields(cls, getattr(cls.__config__, "orig_model"))
        return [cls.from_orm(e) for e in await queryset.prefetch_related(*fetch_fields)]


class PydanticListModel(BaseModel):
    """
    Pydantic BaseModel for List of Tortoise Models

    This provides an extra method above the usual Pydantic
    `model properties <https://pydantic-docs.helpmanual.io/usage/models/#model-properties>`__
    """

    @classmethod
    async def from_queryset(cls, queryset: "QuerySet") -> "PydanticListModel":
        """
        Returns a serializable pydantic model instance that contains a list of models,
        from the provided queryset.

        This will prefetch all the relations automatically.

        :param queryset: a queryset on the model this PydanticListModel is based on.
        """
        submodel = getattr(cls.__config__, "submodel")
        fetch_fields = _get_fetch_fields(submodel, getattr(submodel.__config__, "orig_model"))
        values = cls(
            __root__=[submodel.from_orm(e) for e in await queryset.prefetch_related(*fetch_fields)]
        )
        return values
