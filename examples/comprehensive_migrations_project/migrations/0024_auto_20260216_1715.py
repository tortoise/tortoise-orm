from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import CheckConstraint


class Migration(migrations.Migration):
    dependencies = [("erp", "0023_drop_employee_constraints")]

    initial = False

    operations = [
        ops.AddConstraint(
            model_name="Product",
            constraint=CheckConstraint(check="price > 0", name="ck_product_price_positive"),
        ),
    ]
