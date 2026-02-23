from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0013_add_indexes")]

    initial = False

    operations = [
        ops.RemoveConstraint(
            model_name="Employee",
            name=None,
            fields=["email", "department_id"],
        ),
        ops.AlterField(
            model_name="Order",
            name="customer_email",
            field=fields.CharField(max_length=255),
        ),
    ]
