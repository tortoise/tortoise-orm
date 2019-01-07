from enum import Enum
from functools import partial
from typing import Optional, Union

from pypika.terms import Function
from shapely import geometry
from shapely.geometry.base import BaseGeometry
from shapely.wkt import dumps, loads

from tortoise.fields import Field
from tortoise.function import func


class GeometryType(Enum):
    """
    The currently supported geometry types.
    """
    Point = "POINT"
    Polygon = "POLYGON"

    def to_shapely(self):
        """
        Gets the shapely class for the given database geometry type.
        """

        _shapely_map = {
            "POINT": geometry.Point,
            "POLYGON": geometry.Polygon
        }

        return _shapely_map[self.value]


class GeometryField(Field):
    """
    OpenGIS Geometry field.

    This field represents some of the geometry types in OpenGIS, as defined in `geometry_type`.

    You must provide the following:

    ``geometry_type``:
        The type of geometry used. Refer to :mod:`~tortoise.gis.types` for a full list.

    The following is optional:

    ``srid``:
        The OpenGIS SRID for the column. Defines the projection type. Notable SRID values include:
        - 4326: WGS84 (used in GPS)
    """

    def __init__(
            self,
            geometry_type: GeometryType,
            srid: Optional[int] = None,
            **kwargs
    ) -> None:
        self.geometry_type = geometry_type
        self.srid: int = srid if srid is not None else -1
        super().__init__(geometry_type.to_shapely(), **kwargs)

    def to_python_value(self, value: Optional[Union[bytes, BaseGeometry]]) -> Optional[BaseGeometry]:
        if isinstance(value, bytes):
            return loads(value)
        elif isinstance(value, self.geometry_type.to_shapely()):
            return value
        elif value is None:
            return None
        else:
            raise TypeError("Can't convert %s to %s.", type(value), self.geometry_type.to_shapely())

    def to_db_value(self, value: Optional[Union[bytes]], instance) -> Optional[Function]:
        if isinstance(value, self.geometry_type.to_shapely()):
            value = dumps(value)
        if isinstance(value, str):
            return func.GeomFromText(value, self.srid)
        elif value is None:
            return None
        else:
            raise TypeError("Can't convert %s to wkt-formatted string", type(value))

    def get_sql(self, quote_char="", *args, **kwargs):
        return quote_char + self.model_field_name + quote_char


PointField = partial(GeometryField, GeometryType.Point)
PolygonField = partial(GeometryField, GeometryType.Polygon)
