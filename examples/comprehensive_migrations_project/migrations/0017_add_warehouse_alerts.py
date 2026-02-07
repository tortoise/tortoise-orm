from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    """Add Warehouse and Alert models.

    Alert comes before Warehouse alphabetically, exercising the fix for
    LookupError in CreateModel.state_forward when a FK target model hasn't
    been added to state yet.
    """

    dependencies = [("erp", "0016_delete_audit_log")]

    initial = False

    operations = [
        ops.CreateModel(
            name="Alert",
            fields=[
                ("id", fields.IntField(pk=True)),
                (
                    "warehouse",
                    fields.ForeignKeyField("erp.Warehouse", related_name="alerts"),
                ),
                ("message", fields.TextField()),
                ("is_resolved", fields.BooleanField(default=False)),
                ("created_at", fields.DatetimeField(auto_now_add=True)),
            ],
        ),
        ops.CreateModel(
            name="Warehouse",
            fields=[
                ("id", fields.IntField(pk=True)),
                ("name", fields.CharField(max_length=200)),
                ("location", fields.CharField(max_length=300)),
                ("is_active", fields.BooleanField(default=True)),
            ],
        ),
    ]
