from tortoise import Model, fields
from tortoise.contrib.gis import gis_fields


class GeometryFields(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(255)
    location = gis_fields.PointField(srid=27700, null=True)
    area = gis_fields.PolygonField(srid=27700, null=True)
