from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0018_add_db_defaults")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Product",
            name="stock_quantity",
            field=fields.IntField(db_default=10),
        ),
    ]
