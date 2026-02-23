from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0009_rename_fields")]

    initial = False

    operations = [
        ops.AddField(
            model_name="Employee",
            name="full_name",
            field=fields.CharField(null=True, max_length=255),
        ),
        ops.AddField(
            model_name="Order",
            name="total_amount",
            field=fields.DecimalField(null=True, max_digits=10, decimal_places=2),
        ),
    ]
