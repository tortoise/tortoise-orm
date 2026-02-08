from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0011_populate_computed_fields")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Employee",
            name="full_name",
            field=fields.CharField(max_length=255),
        ),
        ops.AlterField(
            model_name="Order",
            name="total_amount",
            field=fields.DecimalField(max_digits=10, decimal_places=2),
        ),
    ]
