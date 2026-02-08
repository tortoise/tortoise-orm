from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0016_delete_audit_log")]

    initial = False

    operations = [
        ops.CreateModel(
            name="Alert",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                (
                    "warehouse",
                    fields.ForeignKeyField(
                        "erp.Warehouse",
                        source_field="warehouse_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="alerts",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("message", fields.TextField(unique=False)),
                (
                    "is_resolved",
                    fields.BooleanField(default=False, generated=False, null=False, unique=False),
                ),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={
                "table": "alert",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Inventory alert - references Warehouse via FK.",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Warehouse",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                ("name", fields.CharField(max_length=200)),
                ("location", fields.CharField(max_length=300)),
                (
                    "is_active",
                    fields.BooleanField(default=True, generated=False, null=False, unique=False),
                ),
            ],
            options={
                "table": "warehouse",
                "app": "erp",
                "pk_attr": "id",
                "table_description": "Warehouse entity - storage location for inventory.",
            },
            bases=["Model"],
        ),
    ]
