from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("erp", "0007_auto_20260206_0021")]

    initial = False

    operations = [
        ops.RemoveField(model_name="Company", name="temporary_notes"),
        ops.RemoveField(model_name="Department", name="legacy_code"),
        ops.RemoveField(model_name="Employee", name="temp_status"),
    ]
