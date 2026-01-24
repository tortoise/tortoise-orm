from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("accounts", "0002_auto_20260124_1901"),
        ("catalog", "0003_auto_20260124_1901"),
        ("orders", "0001_initial"),
        ("orders", "0002_auto_20260124_1901"),
        ("orders", "0003_auto_20260124_1901"),
    ]

    initial = False

    operations = [
        ops.AddField(
            model_name="User",
            name="last_order",
            field=fields.ForeignKeyField(
                "orders.Order",
                source_field="last_order_id",
                null=True,
                db_constraint=True,
                to_field="id",
                related_name="customers_last_order",
                on_delete=OnDelete.CASCADE,
            ),
        ),
    ]
