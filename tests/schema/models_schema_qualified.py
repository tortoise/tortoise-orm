"""Models with Meta.schema set for testing schema-qualified table generation."""

from tortoise import fields
from tortoise.models import Model


class SchemaCategory(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, description="Category name")

    class Meta:
        table = "category"
        schema = "custom"


class SchemaProduct(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=200)
    category: fields.ForeignKeyRelation[SchemaCategory] = fields.ForeignKeyField(
        "models.SchemaCategory", related_name="products"
    )
    tags: fields.ManyToManyRelation["SchemaTag"] = fields.ManyToManyField(
        "models.SchemaTag", related_name="products", through="product_tags"
    )

    class Meta:
        table = "product"
        schema = "custom"
        table_description = "Products table"


class SchemaTag(Model):
    id = fields.IntField(primary_key=True)
    label = fields.CharField(max_length=50)

    class Meta:
        table = "tag"
        schema = "custom"
