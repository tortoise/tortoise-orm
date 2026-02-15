from tortoise import fields, migrations
from tortoise.fields.db_defaults import Now, RandomHex
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0020_drop_db_default")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="Product",
            name="created_at",
            field=fields.DatetimeField(db_default=Now(), auto_now=False, auto_now_add=False),
        ),
        ops.AddField(
            model_name="Product",
            name="tracking_id",
            field=fields.CharField(null=True, db_default=RandomHex(), max_length=36),
        ),
    ]
