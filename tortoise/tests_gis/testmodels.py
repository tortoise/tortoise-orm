from tortoise import Model, fields
from tortoise.gis import gis_fields


class GeometryFields(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(255)
    location = gis_fields.PointField(srid=4326, null=True)
    area = gis_fields.PolygonField(srid=4326, null=True)
