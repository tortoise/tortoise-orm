from tortoise import Model, fields
from tortoise.contrib.postgres.fields import TSVectorField


class TSVectorEntry(Model):
    id = fields.IntField(primary_key=True)
    title = fields.TextField()
    body = fields.TextField(null=True)
    search_vector = TSVectorField(
        source_fields=("title", "body"),
        config="english",
        weights=("A", "B"),
    )

    class Meta:
        table = "tsvector_entry"
