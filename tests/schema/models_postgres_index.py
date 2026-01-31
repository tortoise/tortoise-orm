from tortoise import Model, fields
from tortoise.contrib.postgres.fields import TSVectorField
from tortoise.contrib.postgres.indexes import (
    BloomIndex,
    BrinIndex,
    GinIndex,
    GistIndex,
    HashIndex,
    PostgreSQLIndex,
    SpGistIndex,
)
from tortoise.contrib.postgres.search import SearchVector


class Index(Model):
    bloom = fields.CharField(max_length=200)
    brin = fields.CharField(max_length=200)
    gin = TSVectorField()
    gist = TSVectorField()
    sp_gist = fields.CharField(max_length=200)
    hash = fields.CharField(max_length=200)
    partial = fields.CharField(max_length=200)
    title = fields.TextField()
    body = fields.TextField()

    class Meta:
        indexes = [
            BloomIndex(fields=("bloom",)),
            BrinIndex(fields=("brin",)),
            GinIndex(fields=("gin",)),
            GistIndex(fields=("gist",)),
            SpGistIndex(fields=("sp_gist",)),
            HashIndex(fields=("hash",)),
            PostgreSQLIndex(fields=("partial",), condition={"id": 1}),
            GinIndex(SearchVector("title", "body", config="english")),
        ]
