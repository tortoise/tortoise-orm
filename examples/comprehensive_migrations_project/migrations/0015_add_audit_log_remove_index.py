from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0014_remove_unused_indexes")]

    initial = False

    operations = [
        ops.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("table_name", fields.CharField(max_length=100)),
                ("action", fields.CharField(max_length=20)),
                ("record_id", fields.IntField()),
                ("timestamp", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={
                "table": "auditlog",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Temporary audit log - will be deleted to demonstrate DeleteModel.",
            },
            bases=["Model"],
        ),
        ops.RemoveIndex(
            model_name="Product",
            name="idx_product_category_active",
            fields=None,
        ),
    ]
