from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("catalog", "0001_initial"),
        ("orders", "0001_initial"),
    ]

    initial = False

    operations = [
        ops.AddField(
            model_name="Order",
            name="user",
            field=fields.ForeignKeyField(
                "accounts.User",
                source_field="user_id",
                null=True,
                db_constraint=True,
                to_field="id",
                related_name="orders",
                on_delete=OnDelete.CASCADE,
            ),
        ),
        ops.AddField(
            model_name="OrderItem",
            name="product",
            field=fields.ForeignKeyField(
                "catalog.Product",
                source_field="product_id",
                null=True,
                db_constraint=True,
                to_field="id",
                related_name="order_items",
                on_delete=OnDelete.CASCADE,
            ),
        ),
    ]
