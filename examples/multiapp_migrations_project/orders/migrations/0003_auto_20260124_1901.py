from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_auto_20260124_1901"),
        ("catalog", "0001_initial"),
        ("catalog", "0002_auto_20260124_1901"),
        ("orders", "0002_auto_20260124_1901"),
    ]

    initial = False

    operations = [
        ops.AddField(
            model_name="Order",
            name="approved_by",
            field=fields.ForeignKeyField(
                "accounts.User",
                source_field="approved_by_id",
                null=True,
                db_constraint=True,
                to_field="id",
                related_name="approved_orders",
                on_delete=OnDelete.CASCADE,
            ),
        ),
    ]
