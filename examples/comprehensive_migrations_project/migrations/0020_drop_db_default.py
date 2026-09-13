from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0019_change_db_default")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Product",
            name="is_active",
            field=fields.BooleanField(default=True),
        ),
    ]
