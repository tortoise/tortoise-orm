from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0017_create_bad_sorted_fk")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Product",
            name="is_active",
            field=fields.BooleanField(default=True, db_default=True),
        ),
        ops.AddField(
            model_name="Product",
            name="stock_quantity",
            field=fields.IntField(db_default=0),
        ),
    ]
