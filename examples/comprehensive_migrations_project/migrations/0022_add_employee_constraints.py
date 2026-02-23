from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import UniqueConstraint


class Migration(migrations.Migration):
    dependencies = [("erp", "0021_add_sql_default_expressions")]

    initial = False

    operations = [
        ops.AddConstraint(
            model_name="Employee",
            constraint=UniqueConstraint(fields=("first_name", "last_name"), name=None),
        ),
        ops.AddConstraint(
            model_name="Employee",
            constraint=UniqueConstraint(
                fields=("email", "department_id"), name="uq_employee_email_dept"
            ),
        ),
    ]
