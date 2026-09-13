from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0022_add_employee_constraints")]

    initial = False

    operations = [
        ops.RemoveConstraint(
            model_name="Employee",
            name=None,
            fields=["first_name", "last_name"],
        ),
        ops.RemoveConstraint(
            model_name="Employee",
            name="uq_employee_email_dept",
            fields=None,
        ),
    ]
