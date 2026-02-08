from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial"), ("catalog", "0002_auto_20260124_1901")]

    initial = False

    operations = [
        ops.AddField(
            model_name="User",
            name="favorite_product",
            field=fields.ForeignKeyField(
                "catalog.Product",
                source_field="favorite_product_id",
                null=True,
                db_constraint=True,
                to_field="id",
                related_name="fans",
                on_delete=OnDelete.CASCADE,
            ),
        ),
    ]
