from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0008_auto_20260206_0025")]

    initial = False

    operations = [
        ops.RenameField(
            model_name="Company",
            old_name="code",
            new_name="company_code",
        ),
        ops.RenameField(
            model_name="Employee",
            old_name="hire_date",
            new_name="joined_date",
        ),
        ops.RenameField(
            model_name="Product",
            old_name="sku",
            new_name="product_code",
        ),
    ]
