from itertools import chain
from typing import Union, Optional

from shapely.geometry.base import BaseGeometry
from shapely.wkt import dumps

from pypika import Field as PyPikaField
from tortoise.fields import Field
from tortoise.function import Function


class GeomFromText(Function):
    """Generates geometry from well known text."""

    def __init__(self, wkt: str, srid: Optional[int] = None, alias=None):
        """
        Generate geometry from the given well-known text.
        :param wkt: The well-known text to insert.
        :param srid: The (optional) SRID to interpret it as..
        :param alias: The alias for the function.
        """
        args = filter(lambda x: x is not None, (wkt, srid))
        super().__init__("GeomFromText", *args, alias=alias)


class AsWKT(Function):
    def __init__(self, field: Field, alias=None):
        super().__init__("AsWKT", field, alias=alias)


class Within(Function):
    """
    Checks if the given field is within another.
    """

    accepted_formats = Union[BaseGeometry, GeomFromText, str, Field]

    def __init__(self,
                 object: Optional[accepted_formats] = None,
                 container: Optional[accepted_formats] = None,
                 object_srid=None, container_srid=None, **kwargs
                 ):
        """
        :param object: The object to check.
        :param container: The object you want to check contains the first.
        :param object_srid: The optional srid of the object.
        :param container_srid: The optional srid of the container.
        :param kwargs: An optional single key and value to filter against a field.
        """

        if object and container and not kwargs:
            object = self.convert_to_db_value(object, object_srid)
            container = self.convert_to_db_value(container, container_srid)
        elif len(kwargs) == 1:
            field, target = chain.from_iterable(kwargs.items())
            object = PyPikaField(field)
            container = self.convert_to_db_value(target, container_srid)
        else:
            raise Exception("SHIT")

        super().__init__("Within", object, container)

    @staticmethod
    def convert_to_db_value(target: accepted_formats, srid=None):
        if isinstance(target, BaseGeometry):
            return GeomFromText(dumps(target), srid)
        if isinstance(target, str):
            return GeomFromText(target, srid)
            # todo validate wkb
        if isinstance(target, Field):
            return PyPikaField(target)
        return target
