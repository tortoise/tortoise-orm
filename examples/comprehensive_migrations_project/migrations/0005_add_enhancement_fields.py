from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0004_add_order_system")]

    initial = False

    operations = [
        ops.AddField(
            model_name="Department",
            name="budget",
            field=fields.DecimalField(null=True, max_digits=12, decimal_places=2),
        ),
        ops.AddField(
            model_name="Department",
            name="closing_time",
            field=fields.TimeField(null=True, auto_now=False, auto_now_add=False),
        ),
        ops.AddField(
            model_name="Department",
            name="opening_time",
            field=fields.TimeField(null=True, auto_now=False, auto_now_add=False),
        ),
        ops.AddField(
            model_name="Product",
            name="processing_time",
            field=fields.TimeDeltaField(
                null=True, description="Average time to fulfill", generated=False, unique=False
            ),
        ),
        ops.AddField(
            model_name="Product",
            name="rating",
            field=fields.FloatField(
                null=True,
                description="Average customer rating 0.0-5.0",
                generated=False,
                unique=False,
            ),
        ),
    ]
