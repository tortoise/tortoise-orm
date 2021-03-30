from tortoise import Model, fields
from tortoise.contrib.mysql.fields import GeometryField
from tortoise.contrib.mysql.indexes import FullTextIndex, SpatialIndex


class Index(Model):
    full_text = fields.TextField()
    geometry = GeometryField()

    class Meta:
        indexes = [
            FullTextIndex(fields={"full_text"}, parser_name="ngram"),
            SpatialIndex(fields={"geometry"}),
        ]
