from tortoise.fields import Field


class GeometryField(Field):
    SQL_TYPE = "GEOMETRY"
