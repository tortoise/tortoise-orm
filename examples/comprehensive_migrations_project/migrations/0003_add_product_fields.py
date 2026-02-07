from orjson import loads

from tortoise import fields, migrations
from tortoise.fields.data import JSON_DUMPS
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0002_add_product_catalog")]

    initial = False

    operations = [
        ops.AddField(
            model_name="Product",
            name="external_id",
            field=fields.UUIDField(null=True),
        ),
        ops.AddField(
            model_name="Product",
            name="metadata",
            field=fields.JSONField(null=True, encoder=JSON_DUMPS, decoder=loads),
        ),
        ops.AddField(
            model_name="Product",
            name="price",
            field=fields.DecimalField(max_digits=10, decimal_places=2),
        ),
    ]
