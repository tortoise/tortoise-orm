from decimal import Decimal

from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0005_add_enhancement_fields")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Category",
            name="priority",
            field=fields.IntField(default=0),
        ),
        ops.AlterField(
            model_name="Company",
            name="name",
            field=fields.CharField(max_length=300),
        ),
        ops.AlterField(
            model_name="Department",
            name="budget",
            field=fields.DecimalField(default=Decimal("0.00"), max_digits=12, decimal_places=2),
        ),
    ]
